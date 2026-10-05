#!/usr/bin/env python3
"""Work out which 3D direction each Realsee cube face actually looks at.

The faces are stored under names (front/back/left/right/up/down) with an
unknown in-plane orientation and unknown mirroring. We score every candidate
by projecting known vertical room-corner edges into the face image and
measuring how much image gradient lies along the projected curve. The correct
convention puts real edges on real edges.
"""
import itertools
import json
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
SRC = os.path.abspath(os.path.join(HERE, "..", "武汉104119325592-房源资料"))
FACES = os.path.join(RAW, "faces")
FACE_NAMES = ["front", "back", "left", "right", "up", "down"]
FLOOR_Y = -1.2180
CAM_Y = 0.0047
S = 256  # scoring resolution


def qmat(q):
    x, y, z, w = q["x"], q["y"], q["z"], q["w"]
    n = np.sqrt(x * x + y * y + z * z + w * w)
    x, y, z, w = x / n, y / n, z / n, w / n
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def gradient(path, size=S):
    im = Image.open(path).convert("L").resize((size, size), Image.BILINEAR)
    a = np.asarray(im, np.float32)
    gx = np.zeros_like(a); gy = np.zeros_like(a)
    gx[:, 1:-1] = a[:, 2:] - a[:, :-2]
    gy[1:-1, :] = a[2:, :] - a[:-2, :]
    return np.sqrt(gx * gx + gy * gy)


def faces_for_candidate(d, k, mirror):
    """Build (right, up, forward) basis for a face looking along local direction d.

    k rotates the image about its own normal; mirror flips the image
    horizontally. Both encode how the face was stored.
    """
    FWD = {
        "up": (0.0, 1.0, 0.0),
        "down": (0.0, -1.0, 0.0),
        "-Z": (0.0, 0.0, -1.0),
        "+X": (1.0, 0.0, 0.0),
        "+Z": (0.0, 0.0, 1.0),
        "-X": (-1.0, 0.0, 0.0),
    }
    fwd = np.array(FWD[d], float)
    r = np.array([1.0, 0.0, 0.0]); u = np.array([0.0, 1.0, 0.0])
    for _ in range(k % 4):
        r, u = u, -r
    if mirror:
        r = -r
    return r, u, fwd


def project(P, C, r, u, fwd, f, size=S):
    """Gnomonic projection of world points into a 90-degree cube face."""
    w = np.atleast_2d(P) - C
    a = w @ fwd
    ok = a > 0.15
    if not ok.any():
        return None
    px = size / 2.0 + f * (w @ r) / np.maximum(a, 1e-6)
    py = size / 2.0 - f * (w @ u) / np.maximum(a, 1e-6)
    return np.stack([px[ok], py[ok]], 1), ok


def sample_grad(g, uv):
    h, w = g.shape
    xi = np.clip(uv[:, 0].astype(int), 0, w - 1)
    yi = np.clip(uv[:, 1].astype(int), 0, h - 1)
    return g[yi, xi]


def score_face(g, obs, corners, d, k, mirror, f):
    R = qmat(obs["quaternion"])
    C = np.array(obs["position"], float)
    r, u, fwd = faces_for_candidate(d, k, mirror)
    r, u, fwd = R @ r, R @ u, R @ fwd
    tot, n = 0.0, 0
    for (cx, cz) in corners:
        for zt in (FLOOR_Y, CAM_Y):
            pr = project(np.array([cx, zt, cz]), C, r, u, fwd, f)
            if pr is None:
                continue
            uv, ok = pr
            if ok.all() and np.all(np.abs(uv[:, 0]) < S) and np.all(np.abs(uv[:, 1]) < S):
                tot += sample_grad(g, uv).sum()
                n += 2
    return tot / max(n, 1)


def main():
    rooms = json.load(open(os.path.join(RAW, "rooms_vr.json")))
    work = json.load(open(os.path.join(SRC, "01-房源信息", "work.json")))
    obs = work["observers"]

    corners = set()
    for rm in rooms:
        for x, z in rm["pts_vr"]:
            corners.add((round(x, 3), round(z, 3)))
    corners = sorted(corners)
    print("unique room corners: %d" % len(corners))

    grads = {}
    for o in obs[:12]:
        for fn in FACE_NAMES:
            grads[(o["index"], fn)] = gradient(os.path.join(FACES, "%d-%s.png" % (o["index"], fn)))

    f = S / 2.0  # 90 deg face
    results = {}
    for fn in FACE_NAMES:
        cands = []
        dirs = ["-Z", "+Z", "+X", "-X", "up", "down"]
        for d in dirs:
            for k in range(4):
                for mir in (False, True):
                    tot = 0.0
                    for o in obs[:12]:
                        g = grads[(o["index"], fn)]
                        near = [c for c in corners
                                if np.hypot(c[0] - o["position"][0], c[1] - o["position"][2]) < 5.0]
                        tot += score_face(g, o, near, d, k, mir, f)
                    cands.append((tot / 12.0, d, k, mir))
        cands.sort(reverse=True)
        results[fn] = cands
        print("\n%s:" % fn)
        for sc, d, k, mir in cands[:4]:
            print("   dir=%-4s rot=%d mirror=%-5s  score=%.2f" % (d, k, mir, sc))
        bsc, d, k, mir = cands[0]
        rsc = cands[1][0]
        print("   -> best %s dir=%s rot=%d mirror=%s   (runner-up %.2f, ratio %.2fx)"
              % (fn, d, k, mir, rsc, bsc / max(rsc, 1e-9)))

    json.dump({fn: {"dir": c[0][1], "rot": c[0][2], "mirror": c[0][3]} for fn, c in results.items()},
              open(os.path.join(RAW, "cube_convention.json"), "w"), indent=2)
    print("\nwrote raw/cube_convention.json")


if __name__ == "__main__":
    main()