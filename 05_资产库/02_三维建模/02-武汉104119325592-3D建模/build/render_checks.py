#!/usr/bin/env python3
"""Render the verification views.

Uses per-category material overrides so the architectural form reads clearly,
which is the point of these images: proof that the 3-D model matches the
measured plan and the real VR viewpoints.

Run:  blender -b model/<blend> -P build/render_checks.py
"""
import json
import math
import os

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
OUT = os.path.abspath(os.path.join(HERE, "..", "renders"))
SRC = os.path.abspath(os.path.join(HERE, "..", "武汉104119325592-房源资料"))

CEIL_H = 2.90


def V(x, y, z):
    return Vector((x, -z, y))


def set_engine(scene, samples=64):
    for name in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = name
            break
        except TypeError:
            continue
    else:
        scene.render.engine = "CYCLES"
        scene.cycles.samples = samples
    try:
        scene.view_settings.view_transform = "Standard"
    except TypeError:
        pass


def override(mat):
    vl = bpy.context.view_layer
    for lc in vl.layer_collection.children:
        if lc.name == "沙湖九号_104119325592":
            lc.material_override = mat
    vl.material_override = mat


def hide(collections, on):
    for name in collections:
        c = bpy.data.collections.get(name)
        if c:
            for ob in c.objects:
                ob.hide_render = on


def look_at(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def _principled(m):
    """Blender renamed the default shader node across versions."""
    for n in m.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            return n
    raise RuntimeError("no Principled BSDF node")


def solid_mat(name, color, rough=0.55):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = _principled(m)
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = rough
    return m


def set_object_materials(collection, material):
    if not collection:
        return
    for ob in collection.objects:
        if ob.type != "MESH":
            continue
        ob.data.materials.clear()
        ob.data.materials.append(material)


def main():
    os.makedirs(OUT, exist_ok=True)
    scene = bpy.context.scene
    reg = json.load(open(os.path.join(RAW, "registration.json")))
    rooms = json.load(open(os.path.join(RAW, "rooms_vr.json")))
    work = json.load(open(os.path.join(SRC, "01-房源信息", "work.json")))
    y0 = reg["floor_y"]
    y1 = y0 + CEIL_H

    xs = [p[0] for r in rooms for p in r["pts_vr"]]
    zs = [p[1] for r in rooms for p in r["pts_vr"]]
    cx, cz = (min(xs) + max(xs)) / 2, (min(zs) + max(zs)) / 2
    span = max(max(xs) - min(xs), max(zs) - min(zs))

    set_engine(scene, samples=96)
    c_cam = bpy.data.collections.new("07_相机")
    scene.collection.children.link(c_cam)

    # distinct category materials for the architectural proof renders
    m_floor = solid_mat("PROOF_地面", (0.86, 0.80, 0.70))
    m_wall = solid_mat("PROOF_墙体", (0.26, 0.28, 0.33))
    m_open = solid_mat("PROOF_门窗", (0.20, 0.50, 0.72))
    set_object_materials(bpy.data.collections.get("01_地面"), m_floor)
    set_object_materials(bpy.data.collections.get("02_墙体"), m_wall)
    set_object_materials(bpy.data.collections.get("03_吊顶"), m_wall)
    set_object_materials(bpy.data.collections.get("04_门窗"), m_open)

    world = scene.world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.42, 0.50, 0.60, 1.0)
    bg.inputs[1].default_value = 0.9
    sun = bpy.data.objects.get("日光")
    if sun:
        sun.data.energy = 2.6

    # ---------- 1. dollhouse ----------
    hide(["03_吊顶", "06_灯光"], True)
    cd = bpy.data.cameras.new("相机_鸟瞰")
    cd.type = "ORTHO"
    cd.ortho_scale = span * 1.22
    cam = bpy.data.objects.new("相机_鸟瞰", cd)
    cam.location = V(cx, y1 + span * 1.70, cz - span * 0.80)
    c_cam.objects.link(cam)
    look_at(cam, V(cx, y0 + 0.4, cz))
    scene.camera = cam
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1400
    scene.render.filepath = os.path.join(OUT, "01_鸟瞰_无吊顶.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", scene.render.filepath)

    # ---------- 2. strict top view to compare with the floor plan ----------
    cd2 = bpy.data.cameras.new("相机_俯视")
    cd2.type = "ORTHO"
    cd2.ortho_scale = span * 1.04
    cam2 = bpy.data.objects.new("相机_俯视", cd2)
    cam2.location = V(cx, y1 + span, cz)
    c_cam.objects.link(cam2)
    look_at(cam2, V(cx, y0, cz))
    scene.camera = cam2
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 1400
    scene.render.filepath = os.path.join(OUT, "02_正俯视_对照户型图.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", scene.render.filepath)

    # ---------- 3. interior views at real VR viewpoints ----------
    hide(["03_吊顶", "06_灯光"], False)
    cd3 = bpy.data.cameras.new("相机_室内")
    cd3.lens = 18.0
    cd3.clip_start = 0.02
    cd3.clip_end = 200
    cam3 = bpy.data.objects.new("相机_室内", cd3)
    c_cam.objects.link(cam3)
    scene.camera = cam3
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080

    def inside(pt, poly):
        x, z = pt
        res = False
        for i in range(len(poly)):
            x1, z1 = poly[i]; x2, z2 = poly[(i + 1) % len(poly)]
            if (z1 > z) != (z2 > z):
                if x < x1 + (z - z1) * (x2 - x1) / (z2 - z1):
                    res = not res
        return res

    targets = [("客厅", 0), ("餐厅", 6), ("厨房", 8), ("卧室C", 27), ("主卧", 17)]
    for label, pref in targets:
        o = next((x for x in work["observers"] if x["index"] == pref), None)
        if o is None:
            continue
        p = o["standing_position"]
        rm = next((r for r in rooms if inside((p[0], p[2]), r["pts_vr"])), None)
        if rm is None:
            continue
        poly = rm["pts_vr"]
        cxr = sum(q[0] for q in poly) / len(poly)
        czr = sum(q[1] for q in poly) / len(poly)
        dx, dz = cxr - p[0], czr - p[1]
        n = math.hypot(dx, dz) or 1.0
        cam3.location = V(p[0], y0 + 1.58, p[1])
        look_at(cam3, V(p[0] + dx / n * 4.0, y0 + 1.35, p[1] + dz / n * 4.0))
        fn = os.path.join(OUT, "03_室内_%s_机位%02d.png" % (rm["name"], pref))
        scene.render.filepath = fn
        bpy.ops.render.render(write_still=True)
        print("rendered", fn)

    print("\ndone ->", OUT)


if __name__ == "__main__":
    main()