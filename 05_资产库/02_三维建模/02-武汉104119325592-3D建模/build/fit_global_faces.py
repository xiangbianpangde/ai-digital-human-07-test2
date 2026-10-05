#!/usr/bin/env python3
"""Determine the cube-face directions with the cube's own constraints.

The four side faces of a panorama must point at four mutually perpendicular
horizontal directions. So instead of fitting each face freely we fit a single
global yaw offset plus the face focal length, scoring every camera and every
side face together. In-plane orientation is assumed to be level (world up),
which is what a levelled tripod cube map uses.
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
S = 448
FLOOR_Y = -1.2180
SIDE = ["front", "back", "left", "right"]


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


def boundary(poly, step=0.05):
    out = []
    for i in range(len(poly)):
        a = np.array(poly[i]); b = np.array(poly[(i + 1) % len(poly)])
        L = float(np.hypot(*(b - a)))
        for t in np.linspace(0, 1, max(int(L / step), 2), endpoint=False):
            out.append(a + (b - a) * t)
    return np.array(out)


def score(g, pts3, C, fwd, f):
    up = np.array([0.0, 1.0, 0.0])
    r = np.cross(up, fwd); r /= np.linalg.norm(r)
    w = pts3 - C
    a = w @ fwd
    ok = a > 0.35
    if ok.sum() < 25:
        return 0.0
    px = S / 2 + f * (w @ r)[ok] / a[ok]
    py = S / 2 - f * (w @ up)[ok] / a[ok]
    vis = (px > 3) & (px < S - 4) & (py > 3) & (py < S - 4)
    if vis.sum() < 25:
        return 0.0
    uv = np.stack([px[vis], py[vis]], 1)
    hit = bilin(g, uv)
    base = (bilin(g, uv + np.array([0, 7])) + bilin(g, uv + np.array([0, -7]))
            + bilin(g, uv + np.array([7, 0])) + bilin(g, uv + np.array([-7, 0]))) / 4.0
    return float(np.mean(hit - base))


def main():
    rooms = json.load(open(os.path.join(RAW, "rooms_vr.json")))
    work = json.load(open(os.path.join(SRC, "01-房源信息", "work.json")))
    obs = work["observers"]

    picks = []
    for o in obs:
        p = o["standing_position"]
        r = room_of((p[0], p[2]), rooms)
        if r is not None and len(boundary(r["pts_vr"])) > 60:
            picks.append((o, r))
    picks = picks[::3]  # spread across the apartment
    print("cameras used: %d" % len(picks))

    grads, pts, C, dirs = {}, {}, {}, {}
    for o, r in picks:
        i = o["index"]
        grads[i] = [grad_of(os.path.join(FACES, "%d-%s.png" % (i, fn))) for fn in SIDE]
        b = boundary(r["pts_vr"])
        pts[i] = np.column_stack([b, np.full(len(b), FLOOR_Y)])
        C[i] = np.array(o["position"], float)
        R = qmat(o["quaternion"])
        d = np.stack([R @ np.array([0.0, 0.0, -1.0]),  # local forward
                      R @ np.array([1.0, 0.0, 0.0]),   # local +X
                      R @ np.array([0.0, 0.0, 1.0]),   # local back
                      R @ np.array([-1.0, 0.0, 0.0])])  # local -X
        d[:, 1] = 0.0
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        dirs[i] = d
        print("  cam %2d room %-5s" % (i, r["name"]), end="")
    print()

    results = []
    for fov in (80, 85, 90, 95, 100):
        f = (S / 2) / math.tan(math.radians(fov / 2.0))
        for shift in range(0, 360, 2):
            th = math.radians(shift)
            ct, st = math.cos(th), math.sin(th)
            tot = 0.0; n = 0
            for o, _ in picks:
                i = o["index"]
                d = dirs[i]
                rot = np.array([[ct, -st], [st, ct]])
                dd = d.copy(); dd[:, 0] = d[:, 0] * ct - d[:, 2] * st
                dd[:, 2] = d[:, 0] * st + d[:, 2] * ct
                for k in range(4):
                    s = score(grads[i][k], pts[i], C[i], dd[k], f)
                    tot += s; n += 1
            results.append((tot / n, fov, shift))
    results.sort(reverse=True)
    print("\ntop global fits (mean contrast score):")
    for sc, fov, sh in results[:10]:
        print("   fov=%3d  yaw_shift=%3d  score=%+.3f" % (fov, sh, sc))
    print("\nmedian score over all candidates: %+.3f" % float(np.median([r[0] for r in results])))
    best = results[0]
    json.dump({"fov_deg": best[1], "yaw_shift_deg": best[2], "score": best[0]},
              open(os.path.join(RAW, "sideface_global.json"), "w"), indent=2)
    print("\nwrote raw/sideface_global.json")


if __name__ == "__main__":
    main()