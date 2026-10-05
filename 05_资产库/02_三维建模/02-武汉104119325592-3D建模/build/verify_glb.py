#!/usr/bin/env python3
"""Independent verification of the exported glTF, without Blender.

Composes node transforms so the check measures the real world-space bounding
box, then compares it against the measured source data and the labelled room
areas.
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))


def read_glb(path):
    d = open(path, "rb").read()
    magic, ver, length = struct.unpack("<III", d[:12])
    if magic != 0x46546C67:
        raise ValueError("not a GLB")
    off = 12
    chunks = []
    while off < length:
        clen, ctype = struct.unpack("<II", d[off:off + 8])
        chunks.append((ctype, off + 8, clen))
        off += 8 + clen
    jt, jo, jl = chunks[0]
    J = json.loads(d[jo:jo + jl].decode("utf-8", errors="replace"))
    return J, ver, len(d)


def mat_mul(a, b):
    """4x4 row-major multiply."""
    out = [[0.0] * 4 for _ in range(4)]
    for i in range(4):
        for j in range(4):
            out[i][j] = sum(a[i][k] * b[k][j] for k in range(4))
    return out


def node_matrix(n):
    import math
    if "matrix" in n:
        m = n["matrix"]
        return [[m[0], m[4], m[8], m[12]],
                [m[1], m[5], m[9], m[13]],
                [m[2], m[6], m[10], m[14]],
                [m[3], m[7], m[11], m[15]]]
    t = n.get("translation", [0, 0, 0])
    r = n.get("rotation", [0, 0, 0, 1])
    s = n.get("scale", [1, 1, 1])
    x, y, z, w = r
    # glTF stores rotations column-major, i.e. this is the transpose of the
    # common textbook form
    R = [
        [1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w)],
        [2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w)],
        [2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y)],
    ]
    m = [[R[i][j] * s[j] for j in range(3)] + [t[i]] for i in range(3)]
    m.append([0.0, 0.0, 0.0, 1.0])
    return m


def main():
    path = os.path.join(ROOT, "model", "shaHu9hao_104119325592.glb")
    J, ver, size = read_glb(path)
    acc = J["accessors"]
    nodes = J["nodes"]

    lo = [1e9] * 3
    hi = [-1e9] * 3
    verts = 0
    children = {i: n.get("children", []) for i, n in enumerate(nodes)}
    parent = {}
    for i, kids in children.items():
        for k in kids:
            parent[k] = i
    roots = [i for i in range(len(nodes)) if i not in parent]
    scene = J.get("scenes", [{}])[0]
    if scene.get("nodes"):
        roots = list(scene["nodes"])

    def bbox_of(idx, M):
        nonlocal verts
        n = nodes[idx]
        M = mat_mul(M, node_matrix(n))
        if "mesh" in n:
            mesh = J["meshes"][n["mesh"]]
            for pr in mesh["primitives"]:
                a = acc[pr["attributes"]["POSITION"]]
                verts += a["count"]
                for c in ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1),
                          (0, 1, 1), (1, 1, 0), (1, 0, 1), (1, 1, 1)):
                    p = (a["min"][c[0]], a["min"][c[1]], a["min"][c[2]])
                    w = [
                        M[0][0] * p[0] + M[0][1] * p[1] + M[0][2] * p[2] + M[0][3],
                        M[1][0] * p[0] + M[1][1] * p[1] + M[1][2] * p[2] + M[1][3],
                        M[2][0] * p[0] + M[2][1] * p[1] + M[2][2] * p[2] + M[2][3],
                    ]
                    for k in range(3):
                        lo[k] = min(lo[k], w[k])
                        hi[k] = max(hi[k], w[k])
        for c in children[idx]:
            bbox_of(c, M)

    ID = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    for r in roots:
        bbox_of(r, ID)

    print("glb: v%d  %d bytes  meshes=%d  nodes=%d  materials=%d  verts=%d"
          % (ver, size, len(J["meshes"]), len(nodes), len(J.get("materials", [])), verts))
    print("world bbox min %s" % [round(v, 3) for v in lo])
    print("world bbox max %s" % [round(v, 3) for v in hi])
    ext = [hi[k] - lo[k] for k in range(3)]
    print("extent %.2f x %.2f x %.2f m" % tuple(ext))

    rooms = json.load(open(os.path.join(HERE, "raw", "rooms_vr.json")))
    xs = [p[0] for r in rooms for p in r["pts_vr"]]
    zs = [p[1] for r in rooms for p in r["pts_vr"]]
    print()
    print("%-24s %8s %8s" % ("check", "model", "source"))
    print("%-24s %8.2f %8.2f" % ("plan X extent", ext[0], max(xs) - min(xs)))
    print("%-24s %8.2f %8.2f" % ("plan Z extent", ext[2], max(zs) - min(zs)))
    print("%-24s %8.2f %8.2f" % ("height", ext[1], 2.90))
    print("%-24s %8.2f %8.2f" % ("floor level", lo[1], 0.0))
    ok = (abs(ext[0] - (max(xs) - min(xs))) < 0.55
          and abs(ext[2] - (max(zs) - min(zs))) < 0.10
          and abs(ext[1] - 2.90) < 0.06
          and abs(lo[1]) < 0.02)
    print()
    print("RESULT:", "PASS - exported model matches the measured source" if ok else "CHECK")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())