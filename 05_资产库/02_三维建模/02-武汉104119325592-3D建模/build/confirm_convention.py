#!/usr/bin/env python3
"""Confirm the derived cube-face convention and fit the ceiling height.

Scores the candidate convention (plus all 8 in-plane roll/mirror variants for
comparison) on the floor-wall and ceiling-wall junctions of every side face,
and sweeps the ceiling height at the same time.
"""
import json
import math
import os

import numpy as np
from PIL import Image

from verify_convention import LOCAL, FACE_ORDER, qmat, inside, room_of, FLOOR_Y, RAW, SRC, FACES, SIDE

S = 384


def bilin(g, uv):
    h, w = g.shape
    x = np.clip(uv[:, 0], 1, w - 2.0); y = np.clip(uv[:, 1], 1, h - 2.0)
    x0 = x.astype(int); y0 = y.astype(int)
    fx = x - x0; fy = y - y0
    return (g[y0, x0] * (1 - fx) * (1 - fy) + g[y0, x0 + 1] * fx * (1 - fy)
            + g[y0 + 1, x0] * (1 - fx) * fy + g[y0 + 1, x0 + 1] * fx * fy)


def grad_of(path):
    a = np.asarray(Image.open(path).convert("L").resize((S, S), Image.BILINEAR), np.float32)
    gx = np.zeros_like(a); gy = np.zeros_like(a)
    gx[:, 1:-1] = a[:, 2:] - a[:, :-2]
    gy[1:-1, :] = a[2:, :] - a[:-2, :]
    return np.sqrt(gx * gx + gy * gy)


def frame(obs, face, roll=0, mirror=False):
    R = qmat(obs["quaternion"])
    fwd = R @ np.array(LOCAL[face], float)
    up = np.array([0.0, 1.0, 0.0])
    r = np.cross(up, fwd); r /= np.linalg.norm(r)
    u = np.cross(fwd, r)
    for _ in range(roll % 4):
        r, u = u, -r
    if mirror:
        r = -r
    return fwd, r, u


def densify(pts, step=0.06):
    out = []
    for i in range(len(pts)):
        a = np.array(pts[i]); b = np.array(pts[(i + 1) % len(pts)])
        L = float(np.hypot(*(b - a)))
        for t in np.linspace(0, 1, max(int(L / step), 2), endpoint=False):
            out.append(a + (b - a) * t)
    return np.array(out)


def score(g, P, C, fwd, r, u, f):
    w = P - C
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
    ctl = (bilin(g, uv + np.array([0, 6])) + bilin(g, uv + np.array([0, -6]))
           + bilin(g, uv + np.array([6, 0])) + bilin(g, uv + np.array([-6, 0]))) / 4.0
    return float(np.mean(hit - ctl))


def main():
    rooms = json.load(open(os.path.join(RAW, "rooms_vr.json")))
    work = json.load(open(os.path.join(SRC, "01-房源信息", "work.json")))
    obs = work["observers"]
    f = S / 2.0
    data = []
    for o in obs[::2]:
        p = o["standing_position"]
        rm = room_of((p[0], p[2]), rooms)
        if rm is None:
            continue
        bd = densify(rm["pts_vr"])
        data.append((o, rm, np.array(o["position"], float), bd))
    print("cameras: %d" % len(data))

    # --- roll / mirror check at H = 2.90 ---
    print("\nin-plane check (mean contrast over all side faces):")
    res = []
    for roll in range(4):
        for mir in (False, True):
            tot = 0.0; n = 0
            for o, rm, C, bd in data:
                P = np.vstack([
                    np.column_stack([bd, np.full(len(bd), FLOOR_Y)]),
                    np.column_stack([bd, np.full(len(bd), FLOOR_Y + 2.90)]),
                    np.array([(q[0], z, q[1]) for q in rm["pts_vr"] for z in
                              np.linspace(FLOOR_Y, FLOOR_Y + 2.90, 7)]),
                ])
                for face in SIDE:
                    g = grad_of(os.path.join(FACES, "%d-%s.png" % (o["index"], face)))
                    fwd, r, u = frame(o, face, roll, mir)
                    tot += score(g, P, C, fwd, r, u, f); n += 1
            res.append((tot / n, roll, mir))
    res.sort(reverse=True)
    for sc, roll, mir in res:
        mark = "  <-- derived convention" if (roll == 0 and not mir) else ""
        print("   roll=%d mirror=%-5s  score=%+.3f%s" % (roll, mir, sc, mark))

    # --- ceiling height sweep with the winning in-plane setting ---
    best = res[0]
    print("\nceiling height sweep (roll=%d mirror=%s):" % (best[1], best[2]))
    out = []
    for H in np.arange(2.40, 3.31, 0.05):
        tot = 0.0; n = 0
        for o, rm, C, bd in data:
            P = np.vstack([
                np.column_stack([bd, np.full(len(bd), FLOOR_Y)]),
                np.column_stack([bd, np.full(len(bd), FLOOR_Y + H)]),
                np.array([(q[0], z, q[1]) for q in rm["pts_vr"] for z in
                          np.linspace(FLOOR_Y, FLOOR_Y + H, 7)]),
            ])
            for face in SIDE:
                g = grad_of(os.path.join(FACES, "%d-%s.png" % (o["index"], face)))
                fwd, r, u = frame(o, face, best[1], best[2])
                tot += score(g, P, C, fwd, r, u, f); n += 1
        out.append((tot / n, float(H)))
    for sc, H in out:
        print("   H=%.2f  score=%+.3f%s" % (H, sc, "  <== best" if sc == max(o[0] for o in out) else ""))
    out.sort(reverse=True)
    print("\nchosen ceiling height: %.2f m" % out[0][1])
    json.dump({"convention": LOCAL, "roll": best[1], "mirror": best[2],
               "ceiling_height_m": out[0][1],
               "h_sweep": [{"ceiling_m": h, "score": s} for s, h in out]},
              open(os.path.join(RAW, "convention_final.json"), "w"), indent=1)


if __name__ == "__main__":
    main()