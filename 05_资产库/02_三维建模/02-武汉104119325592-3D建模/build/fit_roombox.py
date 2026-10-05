#!/usr/bin/env python3
"""Fit face focal length, ceiling height and face orientation together.

A side face should contain the room box: four floor-wall junctions, four
ceiling-wall junctions and four vertical corners. All of those are fixed by
the measured plan once the ceiling height H and the face focal length f are
known. Fitting (f, H, yaw, roll) to image edges therefore determines the cube
convention and the ceiling height at the same time, with no assumptions.
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
S = 384


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


def grad_of(path):
    a = np.asarray(Image.open(path).convert("L").resize((S, S), Image.BILINEAR), np.float32)
    gx = np.zeros_like(a); gy = np.zeros_like(a)
    gx[:, 1:-1] = a[:, 2:] - a[:, :-2]
    gy[1:-1, :] = a[2:, :] - a[:-2, :]
    return np.sqrt(gx * gx + gy * gy)


def densify(pts, step=0.06):
    out = []
    for i in range(len(pts)):
        a = np.array(pts[i]); b = np.array(pts[(i + 1) % len(pts)])
        L = float(np.hypot(*(b - a)))
        for t in np.linspace(0, 1, max(int(L / step), 2), endpoint=False):
            out.append(a + (b - a) * t)
    return np.array(out)


def room_box_points(poly, H, n_vert=9):
    """Floor loop, ceiling loop and vertical corner edges of the room."""
    bd = densify(poly)
    floor = np.column_stack([bd, np.full(len(bd), FLOOR_Y)])
    ceil = np.column_stack([bd, np.full(len(bd), FLOOR_Y + H)])
    verts = []
    zs = np.linspace(FLOOR_Y, FLOOR_Y + H, n_vert)
    for p in poly:
        for z in zs:
            verts.append((p[0], z, p[1]))
    return floor, ceil, np.array(verts)


def basis(yaw, roll):
    a = math.radians(yaw)
    fwd = np.array([math.sin(a), 0.0, math.cos(a)])
    r = np.cross(np.array([0.0, 1.0, 0.0]), fwd)
    r /= np.linalg.norm(r)
    u = np.cross(fwd, r)
    for _ in range(roll % 4):
        r, u = u, -r
    return fwd, r, u


def score(g, pts3, C, fwd, r, u, f):
    w = pts3 - C
    a = w @ fwd
    ok = a > 0.30
    if ok.sum() < 40:
        return 0.0
    px = S / 2 + f * (w @ r)[ok] / a[ok]
    py = S / 2 - f * (w @ u)[ok] / a[ok]
    vis = (px > 4) & (px < S - 5) & (py > 4) & (py < S - 5)
    if vis.sum() < 40:
        return 0.0
    uv = np.stack([px[vis], py[vis]], 1)
    hit = bilin(g, uv)
    ctl = (bilin(g, uv + np.array([0, 5])) + bilin(g, uv + np.array([0, -5]))
           + bilin(g, uv + np.array([5, 0])) + bilin(g, uv + np.array([-5, 0]))) / 4.0
    return float(np.mean(hit - ctl))


def main():
    rooms = json.load(open(os.path.join(RAW, "rooms_vr.json")))
    work = json.load(open(os.path.join(SRC, "01-房源信息", "work.json")))
    obs = work["observers"]

    # prefer bedrooms and corridors: regular rectangles, little clutter
    want = ("卧室A", "卧室B", "卧室C", "卧室D", "过道")
    picks = []
    for o in obs:
        p = o["standing_position"]
        r = room_of((p[0], p[2]), rooms)
        if r is not None and r["name"] in want:
            picks.append((o, r))
    picks = picks[::5]
    print("cameras: %d\n" % len(picks))

    fovs = [85, 90, 95, 100, 105, 112]
    Hs = np.arange(2.55, 3.21, 0.05)
    yaws = list(range(0, 360, 15))
    rolls = [0, 1, 2, 3]

    votes = defaultdict(float)
    for o, r in picks:
        i = o["index"]
        C = np.array(o["position"], float)
        for fn in SIDE:
            g = grad_of(os.path.join(FACES, "%d-%s.png" % (i, fn)))
            local = []
            for H in Hs:
                floor, ceil, verts = room_box_points(r["pts_vr"], float(H))
                P = np.vstack([floor, ceil, verts])
                for fov in fovs:
                    f = (S / 2) / math.tan(math.radians(fov / 2.0))
                    for yaw in yaws:
                        for roll in rolls:
                            fwd, rr, uu = basis(yaw, roll)
                            local.append((score(g, P, C, fwd, rr, uu, f), fov, float(H), yaw, roll))
            local.sort(reverse=True)
            b = local[0]
            print("cam %2d %-5s %-5s -> fov=%3d H=%.2f yaw=%3d roll=%d score=%+.2f"
                  % (i, r["name"], fn, b[1], b[2], b[3], b[4], b[0]))
            votes[(b[1], round(b[2], 2))] += 1.0

    print("\n--- most common (fov, H) across faces ---")
    for k, v in sorted(votes.items(), key=lambda kv: -kv[1])[:12]:
        print("   fov=%3d  H=%.2f   votes=%d" % (k[0], k[1], v))
    json.dump({"votes": {"fov%d_H%.2f" % k: v for k, v in votes.items()}},
              open(os.path.join(RAW, "box_fit_votes.json"), "w"), indent=1)


if __name__ == "__main__":
    main()