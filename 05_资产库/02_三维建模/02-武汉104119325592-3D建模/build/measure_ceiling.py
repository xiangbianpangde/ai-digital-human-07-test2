#!/usr/bin/env python3
"""Measure real ceiling height from the 'up' faces.

The panorama cameras are level (verified: the photogrammetry hole above the
camera is centred in the up face), so an up face looks straight up. The
ceiling-wall cove then projects to the room outline scaled by

    k = f / (H - h_cam),      f = 1024 px for a 90 deg face at 2048 px

Because it is a scaling, the cove radius r(theta) = k * d(theta) is independent
of the face's unknown in-plane rotation. We can therefore average over all
theta and fit a single unknown k per camera - which gives H without needing
the cube-face convention at all.
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
H_CAM = 1.2180
F = 1024.0
NTH = 512


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


def boundary_distances(cam, nth=NTH):
    cam = np.asarray(cam, float)
    """Distance from cam to the room boundary along nth evenly spaced rays."""
    th = np.linspace(0, 2 * np.pi, nth, endpoint=False)
    dirs = np.column_stack([np.cos(th), np.sin(th)])
    # dense sampling along each ray, vectorised by segment crossing
    L = 12.0
    ts = np.linspace(0.02, L, 600)
    P = cam[None, None, :] + ts[None, :, None] * dirs[:, None, :]
    inside_m = np.zeros(P.shape[:2], bool)
    for r in rooms_all:
        poly2 = np.array(r["pts_vr"])
        n = len(poly2)
        ins = np.zeros(P.shape[:2], bool)
        for i in range(n):
            x1, y1 = poly2[i]; x2, y2 = poly2[(i + 1) % n]
            cond = (y1 > P[:, :, 1]) != (y2 > P[:, :, 1])
            with np.errstate(divide="ignore", invalid="ignore"):
                xint = x1 + (P[:, :, 1] - y1) * (x2 - x1) / (y2 - y1)
            ins ^= cond & (P[:, :, 0] < xint)
        inside_m |= ins
    # the first exit from `inside` along each ray is the wall
    out = np.where(inside_m, 0, 1).astype(np.int8)
    first_exit = np.argmax(out, axis=1)
    ok = first_exit < len(ts) - 1
    return ts[np.clip(first_exit, 0, len(ts) - 1)], ok, th


rooms_all = None


def main():
    global rooms_all
    rooms = json.load(open(os.path.join(RAW, "rooms_vr.json")))
    rooms_all = rooms
    work = json.load(open(os.path.join(SRC, "01-房源信息", "work.json")))

    ks = np.arange(150.0, 900.0, 2.0)   # k = px per metre on the ceiling
    results = []
    used = 0
    for o in work["observers"]:
        p = o["standing_position"]
        rm = room_of((p[0], p[2]), rooms)
        if rm is None:
            continue
        cam = np.array([p[0], p[2]], float)
        # reject cameras within 0.35 m of a wall: their cove is out of frame
        d, ok, th = boundary_distances(cam)
        if ok.sum() < 200 or np.percentile(d[ok], 4) < 0.45:
            continue
        im = Image.open(os.path.join(FACES, "%d-up.png" % o["index"])).convert("L")
        a = np.asarray(im, np.float32)
        cx = cy = 1024.0
        gx, gy = np.gradient(a)
        gm = np.sqrt(gx * gx + gy * gy)
        gx = np.abs(gx); gy = np.abs(gy)
        best = (-1e9, None)
        for k in ks:
            r = k * d
            valid = ok & (r < 960) & (r > 150)
            if valid.sum() < 120:
                continue
            # sample the radial gradient exactly at the predicted cove, and a
            # control band 60 px outward (must be on the wall, not the ceiling)
            xs = (cx + r * np.cos(th)).astype(int)
            ys = (cy + r * np.sin(th)).astype(int)
            xo = (cx + (r + 60) * np.cos(th)).astype(int)
            yo = (cy + (r + 60) * np.sin(th)).astype(int)
            inb = (xs >= 0) & (xs < 2048) & (ys >= 0) & (ys < 2048)
            ino = (xo >= 0) & (xo < 2048) & (yo >= 0) & (yo < 2048) & valid
            if ino.sum() < 120:
                continue
            hit = gm[ys[inb], xs[inb]].mean()
            ctl = gm[yo[ino], xo[ino]].mean()
            sc = hit - ctl
            if sc > best[0]:
                best = (sc, k)
        if best[1] is None:
            continue
        H = H_CAM + F / best[1]
        results.append((o["index"], rm["name"], best[1], H, best[0]))
        used += 1
        print("cam %2d %-5s  k=%6.1f px/m  ->  ceiling H = %.2f m   (edge contrast %+.2f)"
              % (o["index"], rm["name"], best[1], H, best[0]))

    Hs = np.array([r[3] for r in results])
    print("\ncameras used: %d" % used)
    print("ceiling height: median %.3f  mean %.3f  std %.3f  min %.2f  max %.2f"
          % (np.median(Hs), Hs.mean(), Hs.std(), Hs.min(), Hs.max()))
    print("interquartile: %.2f .. %.2f" % (np.percentile(Hs, 25), np.percentile(Hs, 75)))
    json.dump({"per_camera": [{"cam": a, "room": b, "k": c, "ceiling_m": d, "score": e}
                              for a, b, c, d, e in results],
               "median_m": float(np.median(Hs)), "mean_m": float(Hs.mean()),
               "std_m": float(Hs.std())},
              open(os.path.join(RAW, "ceiling_height.json"), "w"), indent=1)
    print("\nwrote raw/ceiling_height.json")


if __name__ == "__main__":
    main()