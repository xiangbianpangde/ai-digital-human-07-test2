#!/usr/bin/env python3
"""Verify the cube-face convention and, if it holds, project real photos.

Empirical mapping read off the panorama content of camera 0 and confirmed by
the orientation test: with the level camera frame (+Y up, -Z forward),

    front -> +Z   back -> -Z   left -> -X   right -> +X   up -> +Y   down -> -Y

i.e. the stored face names are the OpenGL-style ones, so front/back are
swapped relative to the Three.js forward axis. Each face is a 90 degree
gnomonic view with world up in-plane.
"""
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
SRC = os.path.abspath(os.path.join(HERE, "..", "武汉104119325592-房源资料"))
FACES = os.path.join(RAW, "faces")
FLOOR_Y = -1.2180
CEIL_H = 2.90
LOCAL = {
    "front": (0.0, 0.0, 1.0),
    "back": (0.0, 0.0, -1.0),
    "left": (-1.0, 0.0, 0.0),
    "right": (1.0, 0.0, 0.0),
    "up": (0.0, 1.0, 0.0),
    "down": (0.0, -1.0, 0.0),
}
FACE_ORDER = ["front", "back", "left", "right", "up", "down"]
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


def face_frame(obs, face):
    R = qmat(obs["quaternion"])
    fwd = R @ np.array(LOCAL[face], float)
    world_up = np.array([0.0, 1.0, 0.0])
    if abs(float(fwd @ world_up)) > 0.9:          # up / down face
        r = R @ np.array([1.0, 0.0, 0.0])
        u = R @ np.cross(np.array([0.0, 0.0, 1.0]), np.array([1.0, 0.0, 0.0]))
        u = r * 0.0 + np.cross(r, fwd)
    else:
        r = np.cross(world_up, fwd)
        r /= np.linalg.norm(r)
        u = np.cross(fwd, r)
    return fwd, r, u


def project(P, C, fwd, r, u, f, size):
    w = np.atleast_2d(np.asarray(P, float)) - C
    a = w @ fwd
    ok = a > 0.12
    if not ok.any():
        return None
    px = size / 2 + f * (w @ r)[ok] / np.maximum(a[ok], 1e-9)
    py = size / 2 - f * (w @ u)[ok] / np.maximum(a[ok], 1e-9)
    return np.stack([px, py], 1)


def overlay(cam, size=380):
    rooms = json.load(open(os.path.join(RAW, "rooms_vr.json")))
    work = json.load(open(os.path.join(SRC, "01-房源信息", "work.json")))
    o = [x for x in work["observers"] if x["index"] == cam][0]
    C = np.array(o["position"], float)
    rm = room_of((o["standing_position"][0], o["standing_position"][2]), rooms)
    f = size / 2.0
    M = Image.new("RGB", (size * 3, size * 2), (0, 0, 0))
    for i, face in enumerate(FACE_ORDER):
        im = Image.open(os.path.join(FACES, "%d-%s.png" % (cam, face))).convert("RGB").resize((size, size), Image.LANCZOS)
        dr = ImageDraw.Draw(im)
        fwd, r, u = face_frame(o, face)
        for lvl, col in ((FLOOR_Y, (0, 255, 255)), (FLOOR_Y + CEIL_H, (255, 255, 0))):
            for k in range(len(rm["pts_vr"])):
                a = rm["pts_vr"][k]; b = rm["pts_vr"][(k + 1) % len(rm["pts_vr"])]
                pa = project([[a[0], lvl, a[1]]], C, fwd, r, u, f, size)
                pb = project([[b[0], lvl, b[1]]], C, fwd, r, u, f, size)
                if pa is not None and pb is not None:
                    dr.line([tuple(pa[0]), tuple(pb[0])], fill=col, width=2)
        for a in rm["pts_vr"]:
            seg = project([[a[0], z, a[1]] for z in np.linspace(FLOOR_Y, FLOOR_Y + CEIL_H, 10)],
                          C, fwd, r, u, f, size)
            if seg is not None and len(seg) > 1:
                dr.line([tuple(p) for p in seg], fill=(255, 40, 40), width=2)
        dr.text((6, 4), face, fill=(255, 255, 255))
        M.paste(im, ((i % 3) * size, (i // 3) * size))
    out = os.path.join(RAW, "verify_cam%d.jpg" % cam)
    M.save(out, quality=90)
    print("cam %d (%s) -> %s" % (cam, rm["name"], out))


if __name__ == "__main__":
    overlay(0)