#!/usr/bin/env python3
"""Build the 3D model of 沙湖九号 4室2厅 (listing 104119325592) in Blender.

Everything is generated from measured data only:
  * 14 room outlines from the Realsee outline SVG, registered into VR space
  * wall thicknesses 116 mm / 232 mm from the SVG wall bars
  * door + window openings detected in the real floor plan
  * floor level -1.218 m from the VR observer standing positions
  * ceiling height 2.90 m (fitted; see build/README-model.md)

Run:  blender -b -P build_model.py
"""
import json
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, ".."))
RAW = os.path.join(HERE, "raw")
EXPORT = os.path.join(OUT, "model")

CEIL_H = 2.90
DOOR_H = 2.05
WIN_SILL, WIN_HEAD = 0.95, 2.35
GLAZE_SILL, GLAZE_HEAD = 0.05, 2.50

# rooms with tiled floors rather than wood
TILED = {"厨房", "卫生间A", "卫生间B", "衣帽间"}
BALCONY = {"阳台A", "阳台B", "阳台C"}


def V(x, y, z):
    """VR (x, y up, z) -> Blender (x, -z, y): keeps the model right-handed."""
    return Vector((x, -z, y))


def load():
    reg = json.load(open(os.path.join(RAW, "registration.json")))
    rooms = json.load(open(os.path.join(RAW, "rooms_vr.json")))
    walls = json.load(open(os.path.join(RAW, "walls.json")))
    ops = json.load(open(os.path.join(RAW, "openings.json")))["openings"]
    return reg, rooms, walls, ops


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.length_unit = "METERS"
    return sc


def coll(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c)
    return c


def mat(name, color, rough=0.6, metallic=0.0, emit=None, emit_str=0.0,
        transmission=0.0, alpha=1.0, ior=1.45):
    m = bpy.data.materials.new(name)
    if hasattr(m, 'use_nodes'):
        m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    b.inputs["IOR"].default_value = ior
    if "Alpha" in b.inputs:
        b.inputs["Alpha"].default_value = alpha
    if transmission and "Transmission Weight" in b.inputs:
        b.inputs["Transmission Weight"].default_value = transmission
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1.0)
        b.inputs["Emission Strength"].default_value = emit_str
    return m


def mesh_from(name, verts, faces, material, collection):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.validate()
    me.update()
    if material:
        me.materials.append(material)
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    return ob


def box(cx, cy, cz, sx, sy, sz, material, collection, name):
    """Box given centre and full sizes in Blender axes.

    The mesh stays centred on its own origin and the centre becomes the object
    location, so callers can then rotate the object about its own centre.
    """
    hx, hy, hz = sx / 2.0, sy / 2.0, sz / 2.0
    v = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
         (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    ob = mesh_from(name, v, f, material, collection)
    ob.location = (cx, cy, cz)
    return ob


def prism(name, poly_xz, y0, y1, material, collection, triangulate=True):
    """Extrude a closed XZ polygon between two heights."""
    n = len(poly_xz)
    verts = [V(x, y0, z) for x, z in poly_xz] + [V(x, y1, z) for x, z in poly_xz]
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, j + n, i + n))
    ob = mesh_from(name, verts, faces, material, collection)
    if triangulate:
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bm.to_mesh(ob.data)
        bm.free()
    ob.data.shade_flat()
    return ob


def earclip(poly):
    """Triangulate a simple (non self-intersecting) 2-D polygon by ear clipping.

    Returns index triples. The measured room outlines are simple polygons, so
    this is both sufficient and deterministic - unlike relying on whatever
    tessellation helper the Blender build happens to expose.
    """
    n = len(poly)
    idx = list(range(n))
    if n < 3:
        return []
    area2 = 0.0
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        area2 += x1 * y2 - x2 * y1
    ccw = area2 > 0
    tris = []
    guard = 0
    while len(idx) > 3 and guard < 4 * n * n:
        guard += 1
        cut = None
        m = len(idx)
        for k in range(m):
            i0 = idx[(k - 1) % m]; i1 = idx[k]; i2 = idx[(k + 1) % m]
            a, b, c = poly[i0], poly[i1], poly[i2]
            cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if (cross > 0) != ccw:
                continue
            ok = True
            for j in idx:
                if j in (i0, i1, i2):
                    continue
                p = poly[j]
                d0 = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
                d1 = (c[0] - b[0]) * (p[1] - b[1]) - (c[1] - b[1]) * (p[0] - b[0])
                d2 = (a[0] - c[0]) * (p[1] - c[1]) - (a[1] - c[1]) * (p[0] - c[0])
                neg = (d0 < 0) or (d1 < 0) or (d2 < 0)
                pos = (d0 > 0) or (d1 > 0) or (d2 > 0)
                if not (neg and pos):
                    ok = False
                    break
            if ok:
                cut = (i0, i1, i2)
                break
        if cut is None:
            break
        tris.append(cut)
        idx.remove(cut[1])
    if len(idx) == 3:
        tris.append(tuple(idx))
    return tris


def slab(name, poly_xz, y, material, collection):
    """Horizontal triangulated polygon (floor / ceiling)."""
    tris = earclip(poly_xz)
    verts = [V(x, y, z) for x, z in poly_xz]
    faces = [t for t in tris if len(set(t)) == 3]
    if not faces:
        return None
    return mesh_from(name, verts, faces, material, collection)


def build_walls(walls, ops, y0, y1, mats, c_struct, c_open):
    """Walls as solid panels, with openings carved out by panel splitting."""
    segs = [("int", w) for w in walls["walls_interior"]] + \
           [("ext", w) for w in walls["walls_exterior"]]
    made = 0
    for kind, w in segs:
        a = Vector(w["a"]); b = Vector(w["b"])
        L = (b - a).length
        if L < 1e-4:
            continue
        d = (b - a) / L
        n = Vector((-d.y, d.x))
        th = w["thickness"]

        # openings that live on this exact segment
        local = []
        for o in ops:
            p0, p1 = Vector(o["p0"]), Vector(o["p1"])
            if abs(p0.y - w["a"][1]) < 1e-3 and abs(w["b"][1] - a.y) < 1e-3 and abs(p1.y - a.y) < 1e-3:
                t0 = (p0 - a).dot(d); t1 = (p1 - a).dot(d)
                if min(t0, t1) > -0.02 and max(t0, t1) < L + 0.02:
                    local.append((min(t0, t1), max(t0, t1), o))
        local.sort()

        def panel(t0, t1, ylo, yhi, tag):
            if t1 - t0 < 1e-4 or yhi - ylo < 1e-4:
                return
            wall_box("%s_%s" % (kind, tag), a, d, th, t0, t1, ylo, yhi,
                     mats["wall"], c_struct)

        made_local = [0]
        cur = 0.0
        for oi, (t0, t1, o) in enumerate(local):
            panel(cur, t0, y0, y1, "solid%d" % made_local[0])
            cur = t1
            sill = y0 + o["sill"]
            head = y0 + o["head"]
            if sill > y0 + 1e-4:
                panel(t0, t1, y0, sill, "sill%d" % made_local[0])
            if head < y1 - 1e-4:
                panel(t0, t1, head, y1, "head%d" % made_local[0])
            _opening_leaf(o, a, d, th, y0, c_open, mats, oi)
        panel(cur, L, y0, y1, "solid%d" % made_local[0])
        made += 1
    return made


def wall_box(name, a, d, thick, t0, t1, ylo, yhi, material, collection, normal_off=0.0):
    """A wall-aligned box in VR space.

    a, d are the wall start and unit direction in VR (x, z). The box runs from
    t0 to t1 along d, is `thick` across, and spans heights ylo..yhi. In Blender
    the axes are (length, thickness, height) because VR y is Blender z.
    """
    L = t1 - t0
    mid = a + d * ((t0 + t1) / 2.0)
    n = Vector((-d.y, d.x))
    mid = mid + n * normal_off
    c = V(mid.x, (ylo + yhi) / 2.0, mid.y)
    ob = box(c.x, c.y, c.z, L, thick, yhi - ylo, material, collection, name)
    ob.rotation_euler = (0.0, 0.0, math.atan2(-d.y, d.x))
    return ob


def _opening_leaf(o, a, d, th, y0, c_open, mats, k):
    p0, p1 = Vector(o["p0"]), Vector(o["p1"])
    t0 = (p0 - a).dot(d)
    t1 = (p1 - a).dot(d)
    t0, t1 = min(t0, t1), max(t0, t1)
    w = t1 - t0
    ylo = y0 + o["sill"]
    yhi = y0 + o["head"]
    h = yhi - ylo

    def place(name, thick, material, off=0.0, dy_lo=None, dy_hi=None):
        return wall_box(name, a, d, thick, t0, t1,
                        ylo if dy_lo is None else dy_lo,
                        yhi if dy_hi is None else dy_hi,
                        material, c_open, normal_off=off)

    t = o["type"]
    if t == "门":
        place("门扇_%02d" % k, 0.045, mats["door"], off=-0.02)
    elif t == "开放式门洞":
        place("门洞收口_%02d" % k, th + 0.02, mats["trim"], dy_lo=yhi - 0.06, dy_hi=yhi)
    elif t == "阳台推拉门":
        place("推拉门框_%02d" % k, th * 0.85, mats["frame"], off=-0.03)
        place("推拉门玻璃_%02d" % k, 0.012, mats["glass"], off=-0.03,
              dy_lo=ylo + 0.06, dy_hi=yhi - 0.06)
    else:
        place("窗框_%02d" % k, th * 0.80, mats["frame"], off=-0.03)
        place("窗玻璃_%02d" % k, 0.012, mats["glass"], off=-0.03,
              dy_lo=ylo + 0.05, dy_hi=yhi - 0.05)
        if o["sill"] > 0.3:
            place("窗台_%02d" % k, th + 0.06, mats["trim"], dy_lo=ylo - 0.04, dy_hi=ylo)


def add_lighting(scene, rooms, y0, y1, c_root):
    """Daylight through the windows plus a ceiling fixture per room."""
    import bpy
    from mathutils import Vector

    world = bpy.data.worlds.new("天空")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes["Background"]
    bg.inputs[0].default_value = (0.55, 0.68, 0.85, 1.0)
    bg.inputs[1].default_value = 0.65

    c_lamp = coll("06_灯光", c_root)

    # sun raking in through the south balconies
    sd = bpy.data.lights.new("日光", "SUN")
    sd.energy = 2.2
    sd.angle = math.radians(2.5)
    sd.color = (1.0, 0.96, 0.90)
    sun = bpy.data.objects.new("日光", sd)
    sun.rotation_euler = (math.radians(52), 0, math.radians(196))
    c_lamp.objects.link(sun)

    panel = mat("灯盘", (1.0, 0.96, 0.88), rough=0.4, emit=(1.0, 0.95, 0.85), emit_str=6.0)

    power = {"客厅": 220, "餐厅": 130, "厨房": 90, "过道": 70, "卧室A": 110,
             "卧室B": 110, "卧室C": 100, "卧室D": 90, "卫生间A": 70,
             "卫生间B": 70, "衣帽间": 45, "阳台A": 40, "阳台B": 40, "阳台C": 40}
    for r in rooms:
        poly = [tuple(p) for p in r["pts_vr"]]
        cx = sum(p[0] for p in poly) / len(poly)
        cz = sum(p[1] for p in poly) / len(poly)
        w = max(p[0] for p in poly) - min(p[0] for p in poly)
        dpt = max(p[1] for p in poly) - min(p[1] for p in poly)

        # flush ceiling fixture
        sz = min(w, dpt) * 0.42
        c = V(cx, y1 - 0.03, cz)
        lamp = box(c.x, c.y, c.z, sz, sz, 0.04, panel, c_lamp, "灯盘_" + r["name"])

        ld = bpy.data.lights.new("灯_" + r["name"], "AREA")
        ld.shape = "SQUARE"
        ld.size = max(sz, 0.35)
        ld.energy = power.get(r["name"], 80)
        ld.color = (1.0, 0.95, 0.88)
        lo = bpy.data.objects.new("灯_" + r["name"], ld)
        lo.location = (c.x, c.y, c.z - 0.06)
        c_lamp.objects.link(lo)
    return c_lamp


def build(reg, rooms, walls, ops):
    scene = clear()
    # Build with the floor at z = 0 so the exported model sits on the ground
    # plane. y0 in the VR data is only the reference for the VR cameras.
    y0 = 0.0
    y1 = CEIL_H

    c_root = coll("沙湖九号_104119325592")
    c_floor = coll("01_地面", c_root)
    c_wall = coll("02_墙体", c_root)
    c_ceil = coll("03_吊顶", c_root)
    c_open = coll("04_门窗", c_root)
    c_furn = coll("05_家具", c_root)

    mats = {
        "wood": mat("地板_木", (0.42, 0.26, 0.12), rough=0.35),
        "marble": mat("地板_客厅石材", (0.72, 0.68, 0.60), rough=0.18),
        "tile": mat("地板_瓷砖", (0.55, 0.56, 0.57), rough=0.25),
        "balc": mat("地板_阳台", (0.46, 0.45, 0.43), rough=0.6),
        "wall": mat("墙面_乳胶漆", (0.83, 0.80, 0.75), rough=0.75),
        "ceil": mat("吊顶_白", (0.92, 0.92, 0.90), rough=0.9),
        "door": mat("门_木", (0.35, 0.22, 0.12), rough=0.4),
        "frame": mat("窗框_深灰", (0.13, 0.13, 0.14), rough=0.4, metallic=0.4),
        "trim": mat("收口_白", (0.9, 0.9, 0.88), rough=0.6),
        "glass": mat("玻璃", (0.7, 0.8, 0.85), rough=0.05, transmission=0.95,
                     alpha=0.25, ior=1.5),
    }

    for r in rooms:
        poly = [tuple(p) for p in r["pts_vr"]]
        if r["name"] in BALCONY:
            m = mats["balc"]
        elif r["name"] in TILED:
            m = mats["tile"]
        elif r["name"] == "客厅":
            m = mats["marble"]
        else:
            m = mats["wood"]
        slab("地板_" + r["name"], poly, y0, m, c_floor)
        slab("吊顶_" + r["name"], poly, y1, mats["ceil"], c_ceil)

    build_walls(walls, ops, y0, y1, mats, c_wall, c_open)
    add_lighting(scene, rooms, y0, y1, c_root)
    return scene, y0, y1, c_root, c_furn, mats


def main():
    reg, rooms, walls, ops = load()
    scene, y0, y1, c_root, c_furn, mats = build(reg, rooms, walls, ops)
    os.makedirs(EXPORT, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(EXPORT, "沙湖九号_104119325592.blend"))
    print("scene built: %d rooms, floor y=%.3f, ceiling y=%.3f" % (len(rooms), y0, y1))
    print("saved", os.path.join(EXPORT, "沙湖九号_104119325592.blend"))


if __name__ == "__main__":
    main()