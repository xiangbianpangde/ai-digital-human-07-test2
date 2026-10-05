#!/usr/bin/env python3
"""Self-check the built scene: counts, dimensions, coverage, overlaps."""
import json
import math
import os

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")


def main():
    reg = json.load(open(os.path.join(RAW, "registration.json")))
    y0 = reg["floor_y"]
    y1 = y0 + 2.90
    print("floor y=%.3f  ceiling y=%.3f  (H=%.2f)" % (y0, y1, y1 - y0))

    groups = ["01_地面", "02_墙体", "03_吊顶", "04_门窗", "06_灯光"]
    tot_tris = 0
    for g in groups:
        c = bpy.data.collections.get(g)
        if not c:
            print("MISSING collection", g)
            continue
        n = 0
        tris = 0
        zs = []
        for ob in c.objects:
            if ob.type != "MESH":
                continue
            n += 1
            tris += len(ob.data.polygons)
            for corner in ob.bound_box:
                zs.append((ob.matrix_world @ Vector(corner)).z)
        tot_tris += tris
        extra = ""
        if zs:
            extra = "  Z range %.3f .. %.3f" % (min(zs), max(zs))
        print("%-10s objects=%4d faces=%6d%s" % (g, n, tris, extra))

    # wall checks
    cw = bpy.data.collections.get("02_墙体")
    if cw:
        areas = []
        for ob in cw.objects:
            if ob.type != "MESH":
                continue
            bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
            dx = max(p.x for p in bb) - min(p.x for p in bb)
            dy = max(p.y for p in bb) - min(p.y for p in bb)
            dz = max(p.z for p in bb) - min(p.z for p in bb)
            areas.append((dx * dy, dz, min(dx, dy)))
        zs = [a[1] for a in areas]
        print("\nwall panels: n=%d" % len(areas))
        print("  height  min %.3f max %.3f  (expect %.2f)" % (min(zs), max(zs), y1 - y0))
        thin = [a[2] for a in areas]
        print("  thinnest dim min %.3f max %.3f" % (min(thin), max(thin)))
        tall = [a for a in areas if a[1] > y1 - y0 - 0.01]
        print("  full-height panels: %d / %d" % (len(tall), len(areas)))
        # total wall footprint (plan area) vs expectation
        fp = 0.0
        for ob in cw.objects:
            if ob.type != "MESH":
                continue
            bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
            fp += (max(p.x for p in bb) - min(p.x for p in bb)) * (max(p.y for p in bb) - min(p.y for p in bb))
        print("  total wall plan area (bbox sum) = %.2f m2" % fp)

    print("\ntotal faces: %d" % tot_tris)


if __name__ == "__main__":
    main()
