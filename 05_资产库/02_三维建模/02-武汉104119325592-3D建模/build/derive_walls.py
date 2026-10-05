#!/usr/bin/env python3
"""Derive the wall network from the measured room outlines.

Steps
  1. split every room edge at any vertex lying on it, so shared edges match;
  2. classify each segment as interior (shared by two rooms) or exterior;
  3. look up the real wall thickness (116 mm / 232 mm) from the SVG wall bars;
  4. find door and window openings by scanning the real floor-plan image for
     white gaps along each wall centreline.

Output: build/raw/walls.json - consumed by the Blender builder.
"""
import json
import math
import os
from collections import defaultdict

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
SRC = os.path.abspath(os.path.join(HERE, "..", "武汉104119325592-房源资料"))
PLAN = os.path.join(SRC, "02-户型图与封面", "真实户型图.jpg")
P = 4  # coordinate rounding, metres


def key(a, b):
    return (a, b) if a <= b else (b, a)


def split_edges(poly, all_pts):
    """Split each polygon edge at intermediate vertices so neighbours match."""
    out = []
    n = len(poly)
    for i in range(n):
        a = np.array(poly[i], float); b = np.array(poly[(i + 1) % n], float)
        L = float(np.hypot(*(b - a)))
        if L < 1e-6:
            continue
        ux = (b - a) / L
        mids = []
        for q in all_pts:
            v = np.array(q, float) - a
            t = float(v @ ux)
            if 1e-4 < t < L - 1e-4:
                perp = abs(float(v[0] * ux[1] - v[1] * ux[0]))
                if perp < 0.012:            # 12 mm tolerance
                    mids.append(t)
        mids = sorted(set(round(t, 4) for t in mids))
        cuts = [0.0] + mids + [L]
        for k in range(len(cuts) - 1):
            t0, t1 = cuts[k], cuts[k + 1]
            p0 = a + ux * t0
            p1 = a + ux * t1
            out.append((key(tuple(np.round(p0, P)), tuple(np.round(p1, P))),
                        p0, p1, float(t1 - t0)))
    return out


def main():
    rooms = json.load(open(os.path.join(RAW, "rooms_vr.json")))
    raw = json.load(open(os.path.join(RAW, "rooms.json")))
    reg = json.load(open(os.path.join(RAW, "registration.json")))
    s = reg["scale_m_per_unit"]
    t = reg["translate"]

    # ---------- 1/2. build the wall segment network ----------
    all_pts = sorted({tuple(np.round(np.array(p, float), P)) for r in rooms for p in r["pts_vr"]})
    seg_rooms = defaultdict(set)
    seg_geom = {}
    for r in rooms:
        for k, a, b, L in split_edges(r["pts_vr"], all_pts):
            seg_rooms[k].add(r["name"])
            seg_geom[k] = (a, b, L)

    interior, exterior = [], []
    for k, who in seg_rooms.items():
        a, b, L = seg_geom[k]
        rec = {"a": [round(float(a[0]), 4), round(float(a[1]), 4)],
               "b": [round(float(b[0]), 4), round(float(b[1]), 4)],
               "len": round(L, 4), "rooms": sorted(who)}
        (interior if len(who) >= 2 else exterior).append(rec)
    print("wall segments: %d interior, %d exterior" % (len(interior), len(exterior)))

    # ---------- 3. real thicknesses from the SVG wall bars ----------
    bars = []
    for sy in raw["symbols"]:
        p = np.array(sy["pts"], float) * s + np.array(t, float)
        w = (p[:, 0].max() - p[:, 0].min()); h = (p[:, 1].max() - p[:, 1].min())
        th, L = (min(w, h), max(w, h))
        if th > 0.35:                       # not a wall bar
            continue
        c = p.mean(0)
        # bar axis is the long direction
        if w >= h:
            u = np.array([p[:, 0].max() - p[:, 0].min(), 0.0])
        else:
            u = np.array([0.0, p[:, 1].max() - p[:, 1].min()])
        n = np.linalg.norm(u)
        bars.append({"c": c, "u": u / n, "len": L, "th": th})

    def thickness_for(a, b):
        d = b - a
        L = float(np.hypot(*d))
        if L < 1e-6:
            return None
        u = d / L
        best = None
        for bar in bars:
            # parallel?
            if abs(float(np.cross(u, bar["u"]))) > 0.12:
                continue
            # bar centre on the wall line?
            rel = bar["c"] - a
            perp = abs(float(rel[0] * u[1] - rel[1] * u[0]))
            along = float(rel @ u)
            if perp > 0.12 or along < -0.25 or along > L + 0.25:
                continue
            if best is None or bar["th"] > best:
                best = bar["th"]
        return best

    for w in interior + exterior:
        a = np.array(w["a"]); b = np.array(w["b"])
        th = thickness_for(a, b)
        if th is None:
            w["thickness"] = 0.232 if w in exterior else 0.116
            w["thickness_src"] = "default"
        else:
            w["thickness"] = round(float(th), 4)
            w["thickness_src"] = "svg-bar"

    from collections import Counter
    print("interior thickness:", dict(Counter(round(w["thickness"], 3) for w in interior)))
    print("exterior thickness:", dict(Counter(round(w["thickness"], 3) for w in exterior)))

    # ---------- 4. openings from the real floor plan ----------
    im = Image.open(PLAN).convert("L")
    A = np.asarray(im)
    dark = A < 90                      # walls are solid black
    ys, xs = np.nonzero(dark)
    bb = (xs.min(), xs.max(), ys.min(), ys.max())
    print("plan wall-pixel bbox x[%d,%d] y[%d,%d]" % bb)

    rx = np.array([w["a"][0] for w in interior + exterior] + [w["b"][0] for w in interior + exterior])
    rz = np.array([w["a"][1] for w in interior + exterior] + [w["b"][1] for w in interior + exterior])
    sx = (bb[1] - bb[0]) / (rx.max() - rx.min())
    sy = (bb[3] - bb[2]) / (rz.max() - rz.min())
    sc = (sx + sy) / 2.0
    ox = bb[0] - rx.min() * sc
    oy = bb[2] - rz.min() * sc
    print("plan image mapping: %.3f px/m, offset (%.1f, %.1f)" % (sc, ox, oy))

    def to_px(x, z):
        return (x * sc + ox, z * sc + oy)

    def white_run(x, z, dx, dz, half_th, length, step=0.01):
        """Sample across the wall band; return (t0,t1) of the widest white gap."""
        n = max(int(length / step), 4)
        ts = np.linspace(0.0, length, n)
        px = (x + dx * ts) * sc + ox
        pz = (z + dz * ts) * sc + oy
        # thickness of the wall in pixels, sampled across +/- half_th
        m = max(int((half_th * 1.15 * sc) / 2), 1)
        offsets = np.linspace(-half_th * 1.15, half_th * 1.15, 2 * m + 1)
        line = []
        for o in offsets:
            qx = np.clip((px - dz * o * sc).astype(int), 0, A.shape[1] - 1)
            qz = np.clip((pz + dx * o * sc).astype(int), 0, A.shape[0] - 1)
            line.append(~dark[qz, qx])
        frac = np.mean(line, axis=0)         # 1 = fully white across the band
        return ts, frac

    openings = []
    for w in interior + exterior:
        a = np.array(w["a"]); b = np.array(w["b"])
        L = float(np.hypot(*(b - a)))
        if L < 0.35:
            continue
        dx, dz = (b - a) / L
        th = w["thickness"]
        ts, frac = white_run(a[0], a[1], dx, dz, th, L)
        if frac.max() < 0.75:
            continue
        # group contiguous samples above threshold
        on = frac > 0.75
        i = 0
        while i < len(on):
            if not on[i]:
                i += 1
                continue
            j = i
            while j + 1 < len(on) and on[j + 1]:
                j += 1
            t0, t1 = ts[i], ts[j]
            wlen = float(t1 - t0)
            if wlen > 0.55:
                p0 = (a[0] + dx * t0, a[1] + dz * t0)
                p1 = (a[0] + dx * t1, a[1] + dz * t1)
                openings.append({
                    "t0": round(t0, 3), "t1": round(t1, 3), "width": round(wlen, 3),
                    "p0": [round(p0[0], 3), round(p0[1], 3)],
                    "p1": [round(p1[0], 3), round(p1[1], 3)],
                    "exterior": w in exterior,
                    "rooms": w["rooms"],
                    "mid": [round((p0[0] + p1[0]) / 2, 3), round((p0[1] + p1[1]) / 2, 3)],
                    "dx": round(float(dx), 4), "dz": round(float(dz), 4),
                    "wall_len": round(L, 3),
                })
            i = j + 1

    print("openings found: %d  (exterior %d, interior %d)"
          % (len(openings), sum(1 for o in openings if o["exterior"]),
             sum(1 for o in openings if not o["exterior"])))
    ws = sorted(o["width"] for o in openings)
    print("opening widths: min %.2f  median %.2f  max %.2f" % (ws[0], ws[len(ws) // 2], ws[-1]))
    for o in sorted(openings, key=lambda o: -o["width"])[:14]:
        print("   %-6s w=%.2f at (%.2f, %.2f) rooms=%s"
              % ("EXT" if o["exterior"] else "INT", o["width"], o["mid"][0], o["mid"][1],
                 "/".join(o["rooms"])))

    json.dump({"floor_y": reg["floor_y"], "walls_interior": interior, "walls_exterior": exterior,
               "openings": openings},
              open(os.path.join(RAW, "walls.json"), "w"), ensure_ascii=False, indent=1)
    print("\nwrote raw/walls.json")


if __name__ == "__main__":
    main()