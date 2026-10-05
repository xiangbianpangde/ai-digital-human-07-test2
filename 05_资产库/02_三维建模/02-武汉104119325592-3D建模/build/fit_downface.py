#!/usr/bin/env python3
"""Calibrate the cube-face projection using the 'down' faces.

A down face looks straight at the floor, so the room's floor outline projects
to a known curve. Fitting the face focal length and in-plane rotation against
image gradients gives the true face convention, which every other face then
follows.
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
S = 384


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


def bilinear(g, uv):
    h, w = g.shape
    x = np.clip(uv[:, 0], 0, w - 1.001); y = np.clip(uv[:, 1], 0, h - 1.001)
    x0 = x.astype(int); y0 = y.astype(int)
    fx = x - x0; fy = y - y0
    return (g[y0, x0] * (1 - fx) * (1 - fy) + g[y0, x0 + 1] * fx * (1 - fy)
            + g[y0 + 1, x0] * (1 - fx) * fy + g[y0 + 1, x0 + 1] * fx * fy)


def inside(pt, poly):
    x, y = pt
    res = False
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y):
            if x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                res = not res
    return res


def room_of(pt, rooms):
    for r in rooms:
        if inside(pt, r["pts_vr"]):
            return r
    return None


def dense_boundary(poly, step=0.05):
    out = []
    for i in range(len(poly)):
        a = np.array(poly[i]); b = np.array(poly[(i + 1) % len(poly)])
        L = np.hypot(*(b - a))
        n = max(int(L / step), 2)
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append(a + (b - a) * t)
    return np.array(out)


def score(g, cam, pts3d, f, rot, mir, h):
    """pts3d are floor-level points; rot/mir define the in-plane image basis."""
    d = pts3d[:, :2] - np.asarray(cam, float)[None, :2]                 # dx, dz in the room plane
    r = np.array([math.cos(rot * math.pi / 2), -math.sin(rot * math.pi / 2)])
    u = np.array([math.sin(rot * math.pi / 2), math.cos(rot * math.pi / 2)])
    if mir:
        r = np.array([r[0], -r[1]])
    a = d @ r
    b = d @ u
    px = S / 2 + f * a / h
    py = S / 2 - f * b / h
    ok = (px > 2) & (px < S - 3) & (py > 2) & (py < S - 3)
    if ok.sum() < 20:
        return 0.0, 0
    return bilinear(g, np.stack([px[ok], py[ok]], 1)).mean(), int(ok.sum())


def main():
    rooms = json.load(open(os.path.join(RAW, "rooms_vr.json")))
    work = json.load(open(os.path.join(SRC, "01-房源信息", "work.json")))
    obs = work["observers"]
    H = 1.2180  # camera height above the floor

    cams = []
    for o in obs:
        p = o["standing_position"]
        r = room_of((p[0], p[2]), rooms)
        if r is not None:
            cams.append((o, r))
    print("cameras with a known room: %d/%d" % (len(cams), len(obs)))

    test = cams[:10]
    grads = {o["index"]: grad_of(os.path.join(FACES, "%d-down.png" % o["index"])) for o, _ in test}
    bnds = {o["index"]: dense_boundary(r["pts_vr"]) for o, r in test}

    results = []
    for fov in range(80, 141, 5):
        f = (S / 2) / math.tan(math.radians(fov / 2.0))
        for rot in range(4):
            for mir in (False, True):
                tot, n = 0.0, 0
                for o, _ in test:
                    p = o["standing_position"]
                    sc, k = score(grads[o["index"]], (p[0], p[2]), bnds[o["index"]], f, rot, mir, H)
                    tot += sc * k; n += k
                results.append((tot / max(n, 1), fov, rot, mir))
    results.sort(reverse=True)
    print("\ndown-face calibration (top 10):")
    for sc, fov, rot, mir in results[:10]:
        print("   fov=%3d deg  rot=%d mirror=%-5s  grad=%.2f" % (fov, rot, mir, sc))
    best = results[0]
    print("\nbest: fov=%d deg, in-plane rot=%d, mirror=%s (ratio over 5th: %.2fx)"
          % (best[1], best[2], best[3], best[0] / max(results[4][0], 1e-9)))
    json.dump({"fov_deg": best[1], "rot": best[2], "mirror": best[3],
               "camera_height_m": H, "score": best[0]},
              open(os.path.join(RAW, "downface_calib.json"), "w"), indent=2)


if __name__ == "__main__":
    main()