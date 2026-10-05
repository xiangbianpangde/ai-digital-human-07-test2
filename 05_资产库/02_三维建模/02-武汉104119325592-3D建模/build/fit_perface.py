#!/usr/bin/env python3
"""Unconstrained fit of each side face: look direction + in-plane roll.

Nothing is assumed about the quaternion convention. For each side face we sweep
yaw and in-plane roll at 90 deg face FOV and score how well the projected
floor-wall junction lands on image structure. If the model is right the four
recovered directions must come out 90 deg apart for every camera.
"""
import json
import math
import os
import sys
from collections import defaultdict

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
SRC = os.path.abspath(os.path.join(HERE, "..", "武汉104119325592-房源资料"))
FACES = os.path.join(RAW, "faces")
FLOOR_Y = -1.2180
SIDE = ["front", "back", "left", "right"]
S = 448


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


def grad_of(path):
    a = np.asarray(Image.open(path).convert("L").resize((S, S), Image.BILINEAR), np.float32)
    gx = np.zeros_like(a); gy = np.zeros_like(a)
    gx[:, 1:-1] = a[:, 2:] - a[:, :-2]
    gy[1:-1, :] = a[2:, :] - a[:-2, :]
    return np.sqrt(gx * gx + gy * gy)


def basis(yaw, roll):
    a = math.radians(yaw)
    fwd = np.array([math.sin(a), 0.0, math.cos(a)])
    r = np.cross(np.array([0.0, 1.0, 0.0]), fwd)
    r /= np.linalg.norm(r)
    u = np.cross(fwd, r)
    for _ in range(roll % 4):
        r, u = u, -r
    return fwd, r, u


def score(g, pts3, C, fwd, r, u, f, gmean):
    w = pts3 - C
    a = w @ fwd
    ok = a > 0.35
    if ok.sum() < 25:
        return 0.0
    px = S / 2 + f * (w @ r)[ok] / a[ok]
    py = S / 2 - f * (w @ u)[ok] / a[ok]
    vis = (px > 3) & (px < S - 4) & (py > 3) & (py < S - 4)
    if vis.sum() < 25:
        return 0.0
    uv = np.stack([px[vis], py[vis]], 1)
    hit = bilin(g, uv)
    far = (bilin(g, uv + np.array([0, 40])) + bilin(g, uv + np.array([0, -40]))
           + bilin(g, uv + np.array([40, 0])) + bilin(g, uv + np.array([-40, 0]))) / 4.0
    return float(np.mean(hit) - np.mean(far))


def main():
    rooms = json.load(open(os.path.join(RAW, "rooms_vr.json")))
    work = json.load(open(os.path.join(SRC, "01-房源信息", "work.json")))
    obs = work["observers"]
    f = (S / 2) / math.tan(math.radians(45))

    picks = []
    for o in obs:
        p = o["standing_position"]
        r = room_of((p[0], p[2]), rooms)
        if r is not None:
            picks.append((o, r))
    test = picks[::4]
    print("testing %d cameras\n" % len(test))

    allres = []
    for o, r in test:
        i = o["index"]
        C = np.array(o["position"], float)
        b = boundary(r["pts_vr"])
        pts3 = np.column_stack([b, np.full(len(b), FLOOR_Y)])
        for fn in SIDE:
            g = grad_of(os.path.join(FACES, "%d-%s.png" % (i, fn)))
            gm = float(g.mean())
            best = []
            for yaw in range(0, 360, 2):
                for roll in range(4):
                    fwd, rr, uu = basis(yaw, roll)
                    sc = score(g, pts3, C, fwd, rr, uu, f, gm)
                    best.append((sc, yaw, roll))
            best.sort(reverse=True)
            allres.append((i, fn, best[0][0], best[0][1], best[0][2],
                           float(np.median([b0[0] for b0 in best]))))
            print("cam %2d %-4s room %-5s -> yaw=%3d roll=%d score=%+.2f (median %+.2f)"
                  % (i, fn, r["name"], best[0][1], best[0][2], best[0][0],
                     float(np.median([b0[0] for b0 in best]))))

    print("\n--- per-camera angular spacing of the four recovered directions ---")
    bycam = defaultdict(dict)
    for i, fn, sc, yaw, roll, med in allres:
        bycam[i][fn] = (yaw, roll, sc)
    for i, d in bycam.items():
        if len(d) < 4:
            continue
        ys = sorted(v[0] % 360 for v in d.values())
        gaps = [(ys[(k + 1) % 4] - ys[k]) % 360 for k in range(4)]
        print("cam %2d yaws=%s gaps=%s" % (i, ys, gaps))

    json.dump({str(i): {fn: {"yaw": v[0], "roll": v[1], "score": v[2]} for fn, v in d.items()}
               for i, d in bycam.items()},
              open(os.path.join(RAW, "perface_fit.json"), "w"), indent=1)


if __name__ == "__main__":
    main()