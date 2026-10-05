#!/usr/bin/env python3
"""Overlay predicted room structure on real cube faces for visual verification."""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
SRC = os.path.abspath(os.path.join(HERE, "..", "武汉104119325592-房源资料"))
FACES = os.path.join(RAW, "faces")
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


def main():
    cam = int(sys.argv[1])
    fov = float(sys.argv[2])
    shift = float(sys.argv[3])
    rooms = json.load(open(os.path.join(RAW, "rooms_vr.json")))
    work = json.load(open(os.path.join(SRC, "01-房源信息", "work.json")))
    o = [x for x in work["observers"] if x["index"] == cam][0]
    C = np.array(o["position"], float)
    rm = room_of((o["standing_position"][0], o["standing_position"][2]), rooms)
    R = qmat(o["quaternion"])
    d = np.stack([R @ np.array([0.0, 0.0, -1.0]), R @ np.array([1.0, 0.0, 0.0]),
                  R @ np.array([0.0, 0.0, 1.0]), R @ np.array([-1.0, 0.0, 0.0])])
    d[:, 1] = 0.0
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    th = math.radians(shift); ct, st = math.cos(th), math.sin(th)
    dd = d.copy()
    dd[:, 0] = d[:, 0] * ct - d[:, 2] * st
    dd[:, 2] = d[:, 0] * st + d[:, 2] * ct

    T = 340
    M = Image.new("RGB", (T * 4, T), (0, 0, 0))
    f = (T / 2) / math.tan(math.radians(fov / 2))
    up = np.array([0.0, 1.0, 0.0])
    for k, fn in enumerate(SIDE):
        im = Image.open(os.path.join(FACES, "%d-%s.png" % (cam, fn))).convert("RGB").resize((T, T), Image.LANCZOS)
        dr = ImageDraw.Draw(im)
        fwd = dd[k]
        r = np.cross(up, fwd); r /= np.linalg.norm(r)
        def pr(p):
            w = np.array(p, float) - C
            a = w @ fwd
            if a <= 0.3:
                return None
            return (T / 2 + f * (w @ r) / a, T / 2 - f * (w @ up) / a)
        poly = rm["pts_vr"]
        for i in range(len(poly)):
            a = poly[i]; b = poly[(i + 1) % len(poly)]
            pa = pr([a[0], FLOOR_Y, a[1]]); pb = pr([b[0], FLOOR_Y, b[1]])
            if pa and pb:
                dr.line([pa, pb], fill=(0, 255, 255), width=2)
            seg = [pr([a[0], z, a[1]]) for z in np.linspace(FLOOR_Y, 0.0, 10)]
            seg = [s for s in seg if s]
            if len(seg) > 1:
                dr.line(seg, fill=(255, 40, 40), width=2)
        dr.text((6, 4), fn, fill=(255, 255, 0))
        M.paste(im, (k * T, 0))
    out = os.path.join(RAW, "check_%d_f%g_s%g.png" % (cam, fov, shift))
    M.save(out)
    print("cam %d room %s -> %s" % (cam, rm["name"], out))


main()