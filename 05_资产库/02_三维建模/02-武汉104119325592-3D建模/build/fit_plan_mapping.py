#!/usr/bin/env python3
"""Fit the floor-plan image -> VR coordinate mapping.

The plan drawing's own dimension chains are also black, so a pixel bounding
box is useless. Instead we sample every wall centreline we derived and find
the similarity transform (rotation, scale, translation) that puts all of them
on the darkest pixels in the drawing - the wall strokes themselves.
"""
import json
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
SRC = os.path.abspath(os.path.join(HERE, "..", "武汉104119325592-房源资料"))
PLAN = os.path.join(SRC, "02-户型图与封面", "真实户型图.jpg")
STEP = 0.02


def load():
    walls = json.load(open(os.path.join(RAW, "walls.json")))
    rooms = json.load(open(os.path.join(RAW, "rooms_vr.json")))
    A = np.asarray(Image.open(PLAN).convert("L"))
    pts = []
    for grp in ("walls_interior", "walls_exterior"):
        for w in walls[grp]:
            a = np.array(w["a"]); b = np.array(w["b"])
            L = float(np.hypot(*(b - a)))
            n = max(int(L / STEP), 2)
            ts = np.linspace(0.05, 0.95, n)
            pts.append(a[None, :] + (b - a)[None, :] * ts[:, None])
    return A, np.vstack(pts), walls, rooms


def dark_fraction(A, P, th, sc, tx, ty):
    ct, st = np.cos(np.radians(th)), np.sin(np.radians(th))
    x = P[:, 0] * ct - P[:, 1] * st
    y = P[:, 0] * st + P[:, 1] * ct
    px = np.clip((x * sc + tx).astype(int), 0, A.shape[1] - 1)
    py = np.clip((y * sc + ty).astype(int), 0, A.shape[0] - 1)
    return float((A[py, px] < 110).mean())


def main():
    A, P, walls, rooms = load()
    xs = np.array([p[0] for p in P]); ys = np.array([p[1] for p in P])
    print("wall centreline samples: %d" % len(P))
    print("plan image: %dx%d" % (A.shape[1], A.shape[0]))

    best = None
    # coarse
    for th in np.arange(-3.0, 3.01, 0.5):
        ct, st = np.cos(np.radians(th)), np.sin(np.radians(th))
        x = P[:, 0] * ct - P[:, 1] * st
        y = P[:, 0] * st + P[:, 1] * ct
        for sc in np.arange(98.0, 156.0, 2.0):
            px = x * sc
            py = y * sc
            # align wall bbox to drawing centre, then sweep the offset
            bx = (px.max() + px.min()) / 2
            by = (py.max() + py.min()) / 2
            for tx in np.arange(A.shape[1] / 2 - bx - 40, A.shape[1] / 2 - bx + 41, 8.0):
                for ty in np.arange(A.shape[0] / 2 - by - 40, A.shape[0] / 2 - by + 41, 8.0):
                    f = dark_fraction(A, P, th, sc, tx, ty)
                    if best is None or f > best[0]:
                        best = (f, th, sc, tx, ty)
    print("coarse: dark=%.3f th=%.2f sc=%.2f tx=%.1f ty=%.1f" % best)

    # refine
    for span, step in ((1.5, 0.2), (0.5, 0.06), (0.15, 0.02)):
        f0, th0, sc0, tx0, ty0 = best
        for th in np.arange(th0 - span, th0 + span + 1e-9, step):
            for sc in np.arange(sc0 - span * 3, sc0 + span * 3 + 1e-9, step * 3):
                for tx in np.arange(tx0 - span * 20, tx0 + span * 20 + 1e-9, step * 20):
                    for ty in np.arange(ty0 - span * 20, ty0 + span * 20 + 1e-9, step * 20):
                        f = dark_fraction(A, P, th, sc, tx, ty)
                        if f > best[0]:
                            best = (f, th, sc, tx, ty)
    f, th, sc, tx, ty = best
    print("refined: dark=%.3f  rotation=%.3f deg  scale=%.3f px/m  t=(%.1f, %.1f)"
          % (f, th, sc, tx, ty))

    ct, st = np.cos(np.radians(th)), np.sin(np.radians(th))
    gx = (xs * ct - ys * st) * sc + tx
    gy = (xs * st + ys * ct) * sc + ty
    print("wall lines map to x[%.0f,%.0f] y[%.0f,%.0f]" % (gx.min(), gx.max(), gy.min(), gy.max()))
    out = {"rotation_deg": float(th), "scale_px_per_m": float(sc),
           "translate_px": [float(tx), float(ty)], "dark_fraction": float(f)}
    json.dump(out, open(os.path.join(RAW, "plan_mapping.json"), "w"), indent=2)
    print("wrote raw/plan_mapping.json")


if __name__ == "__main__":
    main()