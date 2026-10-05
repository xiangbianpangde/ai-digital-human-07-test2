#!/usr/bin/env python3
"""Find the true 3D direction of each cube face by continuous search.

For a face image we sweep yaw/pitch and score how strongly the projected
floor-wall junction of the camera's room lines up with image structure. The
score is contrast-corrected: the same curve sampled a few pixels off-line acts
as its own baseline, so a hit has to beat its own neighbourhood.
"""
import json
import math
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
SRC = os.path.abspath(os.path.join(HERE, "..", "武汉104119325592-房源资料"))
FACES = os.path.join(RAW, "faces")
S = 512
FLOOR_Y = -1.2180


def qmat(q):
    x, y, z, w = q["x"], q["y"], q["z"], q["w"]
    n = math.sqrt(x * x + y * y + z * z + w * w)
    x, y, z, w = x / n, y / n, z / n, w / n
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def grad_of(path):
    a = np.asarray(Image.open(path).convert("L").resize((S, S), Image.BILINEAR), np.float32)
    gx = np.zeros_like(a); gy = np.zeros_like(a)
    gx[:, 1:-1] = a[:, 2:] - a[:, :-2]
    gy[1:-1, :] = a[2:, :] - a[:-2, :]
    return np.sqrt(gx * gx + gy * gy)


def bilin(g, uv):
    h, w = g.shape
    x = np.clip(uv[:, 0], 1, w - 2.0); y = np.clip(uv[:, 1], 1, h - 2.0)
    x0 = x.astype(int); y0 = y.astype(int)
    fx = x - x0; fy = y - y0
    return (g[y0, x0] * (1 - fx) * (1 - fy) + g[y0, x0 + 1] * fx * (1 - fy)
            + g[y0 + 1, x0] * (1 - fx) * fy + g[y0 + 1, x0 + 1] * fx * fy)


def inside(pt, poly):
    x, y = pt
    res = False
    for i in range(len(poly)):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y):
            if x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                res = not res
    return res


def room_of(pt, rooms):
    for r in rooms:
        if inside(pt, r["pts_vr"]):
            return r
    return None


def boundary(poly, step=0.04):
    out = []
    for i in range(len(poly)):
        a = np.array(poly[i]); b = np.array(poly[(i + 1) % len(poly)])
        L = float(np.hypot(*(b - a)))
        for t in np.linspace(0, 1, max(int(L / step), 2), endpoint=False):
            out.append(a + (b - a) * t)
    return np.array(out)


def project(pts3, C, fwd, up_ref, f):
    w = pts3 - C
    a = w @ fwd
    ok = a > 0.35
    if ok.sum() < 30:
        return None
    up = np.cross(fwd, up_ref)
    up /= np.linalg.norm(up)
    r = np.cross(up, fwd)
    px = S / 2 + f * (w @ r) / np.maximum(a, 1e-9)
    py = S / 2 - f * (w @ up) / np.maximum(a, 1e-9)
    px, py, ok = px[ok], py[ok], ok
    vis = (px > 3) & (px < S - 4) & (py > 3) & (py < S - 4)
    if vis.sum() < 30:
        return None
    return np.stack([px[vis], py[vis]], 1)


def contrast_score(g, uv, offs=(0, 6, -6, 12, -12)):
    hit = bilin(g, uv)
    base = np.mean([bilin(g, uv + np.array([0, o])) for o in offs[1:]], axis=0)
    return float(np.mean(hit - base)), int(len(uv))


def main():
    rooms = json.load(open(os.path.join(RAW, "rooms_vr.json")))
    work = json.load(open(os.path.join(SRC, "01-房源信息", "work.json")))
    obs = {o["index"]: o for o in work["observers"]}

    cam = 0
    o = obs[cam]
    C = np.array(o["position"], float)
    rm = room_of((o["standing_position"][0], o["standing_position"][2]), rooms)
    bd = boundary(rm["pts_vr"])
    pts3 = np.column_stack([bd, np.full(len(bd), FLOOR_Y)])
    print("cam %d in %s ; %d boundary samples" % (cam, rm["name"], len(bd)))

    for fov in (85, 90, 95, 100):
        f = (S / 2) / math.tan(math.radians(fov / 2.0))
        for face in ("front", "back", "left", "right"):
            g = grad_of(os.path.join(FACES, "%d-%s.png" % (cam, face)))
            res = []
            for yaw in range(0, 360, 3):
                a = math.radians(yaw)
                fwd = np.array([math.sin(a), 0.0, math.cos(a)])
                uv = project(pts3, C, fwd, np.array([0.0, 1.0, 0.0]), f)
                if uv is None:
                    continue
                sc, n = contrast_score(g, uv)
                res.append((sc, yaw, n))
            res.sort(reverse=True)
            b = res[0]
            print("fov=%3d %-6s best yaw=%3d (score %+.2f, n=%d) | 2nd yaw=%3d (%+.2f) | mean %+.2f"
                  % (fov, face, b[1], b[0], b[2], res[1][1], res[1][0],
                     float(np.mean([r[0] for r in res]))))
        print()


if __name__ == "__main__":
    main()