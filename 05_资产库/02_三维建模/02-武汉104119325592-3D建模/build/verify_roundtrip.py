#!/usr/bin/env python3
"""Round-trip check: import the exported glTF and measure the result.

Loading the exported file back is the honest test - it verifies the file that
a viewer will actually open, not the scene we started from.

Run:  blender -b --factory-startup -P build/verify_roundtrip.py
"""
import json
import os

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))


def main():
    glb = os.path.join(ROOT, "model", "shaHu9hao_104119325592.glb")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)

    lo = [1e9] * 3
    hi = [-1e9] * 3
    n_mesh = 0
    n_tris = 0
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        n_mesh += 1
        n_tris += sum(len(p.vertices) - 2 for p in ob.data.polygons)
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            for k in range(3):
                lo[k] = min(lo[k], w[k])
                hi[k] = max(hi[k], w[k])

    ext = [hi[k] - lo[k] for k in range(3)]
    print("imported meshes=%d triangles=%d" % (n_mesh, n_tris))
    print("bbox min %s" % [round(v, 3) for v in lo])
    print("bbox max %s" % [round(v, 3) for v in hi])
    print("extent %.2f x %.2f x %.2f m" % tuple(ext))

    rooms = json.load(open(os.path.join(HERE, "raw", "rooms_vr.json")))
    xs = [p[0] for r in rooms for p in r["pts_vr"]]
    zs = [p[1] for r in rooms for p in r["pts_vr"]]
    src_x = max(xs) - min(xs)
    src_z = max(zs) - min(zs)

    # glTF is Y-up on disk; importing it back into Blender restores Z-up, so in
    # this scene X / Y are the plan extents and Z is the height.
    # Room outlines are the inner wall faces, so the solid walls add about half
    # a wall thickness (116 mm) at each edge.
    WALL_PAD = 0.12
    checks = [
        ("plan X extent", ext[0], src_x + 2 * WALL_PAD, 0.10),
        ("plan Z extent", ext[1], src_z + 2 * WALL_PAD, 0.10),
        ("height", ext[2], 2.90, 0.05),
        ("floor at origin", lo[2], 0.0, 0.01),
        ("ceiling at 2.90", hi[2], 2.90, 0.02),
    ]
    print()
    print("%-20s %8s %8s %7s" % ("check", "model", "source", "tol"))
    ok = True
    for name, got, want, tol in checks:
        good = abs(got - want) <= tol
        ok &= good
        print("%-20s %8.3f %8.3f %7.2f  %s" % (name, got, want, tol, "ok" if good else "FAIL"))
    print()
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())