#!/usr/bin/env python3
"""Find real door and window openings from the floor plan drawing.

Using the fitted plan-image mapping we walk each wall centreline and look for
white gaps across the wall band. Gaps become openings; their width and the
rooms they connect decide whether they are a door, a window or a balcony
sliding door, and that sets the opening height above the floor.
"""
import json
import os
from collections import defaultdict

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
SRC = os.path.abspath(os.path.join(HERE, "..", "武汉104119325592-房源资料"))
PLAN = os.path.join(SRC, "02-户型图与封面", "真实户型图.jpg")

DOOR_H = 2.05
WIN_SILL, WIN_HEAD = 0.95, 2.35
GLAZE_SILL, GLAZE_HEAD = 0.05, 2.50
CEIL_H = 2.90
STEP = 0.01
WHITE = 0.58


def main():
    walls = json.load(open(os.path.join(RAW, "walls.json")))
    mp = json.load(open(os.path.join(RAW, "plan_mapping.json")))
    rooms = {r["name"]: r for r in json.load(open(os.path.join(RAW, "rooms_vr.json")))}

    A = np.asarray(Image.open(PLAN).convert("L"))
    dark = A < 110
    th_r = np.radians(mp["rotation_deg"])
    ct, st = np.cos(th_r), np.sin(th_r)
    sc = mp["scale_px_per_m"]
    tx, ty = mp["translate_px"]

    def to_px(x, z):
        rx = x * ct - z * st
        rz = x * st + z * ct
        return rx * sc + tx, rz * sc + ty

    allw = [("int", w) for w in walls["walls_interior"]] + [("ext", w) for w in walls["walls_exterior"]]
    allw.sort(key=lambda t: -t[1]["len"])

    openings = []
    for kind, w in allw:
        a = np.array(w["a"]); b = np.array(w["b"])
        L = float(np.hypot(*(b - a)))
        if L < 0.30:
            continue
        dx, dz = (b - a) / L
        th = w["thickness"]
        n = max(int(L / STEP), 8)
        ts = np.linspace(0.0, L, n)
        mx, mz = (a[0] + dx * ts), (a[1] + dz * ts)
        # sample a band slightly wider than the wall
        # keep the samples near the centreline so window frame lines,
        # which sit at the wall faces, are not mistaken for solid wall
        offs = np.linspace(-th * 0.42, th * 0.42, 5)
        cols = []
        for o in offs:
            px, py = to_px(mx - dz * o, mz + dx * o)
            cols.append(A[np.clip(py.astype(int), 0, A.shape[0] - 1),
                     np.clip(px.astype(int), 0, A.shape[1] - 1)] > 150)
        frac = np.mean(cols, axis=0)

        on = frac > WHITE
        i = 0
        while i < len(on):
            if not on[i]:
                i += 1
                continue
            j = i
            while j + 1 < len(on) and on[j + 1]:
                j += 1
            t0, t1 = ts[i], ts[j]
            wid = float(t1 - t0)
            i = j + 1
            if wid < 0.55:
                continue
            mid_t = 0.5 * (t0 + t1)
            p0 = (a[0] + dx * t0, a[1] + dz * t0)
            p1 = (a[0] + dx * t1, a[1] + dz * t1)
            mid = (0.5 * (p0[0] + p1[0]), 0.5 * (p0[1] + p1[1]))

            rs = w["rooms"]
            touches_balcony = any(r.startswith("阳台") for r in rs)
            if kind == "int":
                if touches_balcony and wid > 1.2:
                    otype, sill, head = "阳台推拉门", 0.02, GLAZE_HEAD
                elif wid > 1.2:
                    otype, sill, head = "开放式门洞", 0.0, CEIL_H
                else:
                    otype, sill, head = "门", 0.0, DOOR_H
            else:
                if wid >= 2.1:
                    otype, sill, head = "落地窗/阳台门", GLAZE_SILL, GLAZE_HEAD
                else:
                    otype, sill, head = "窗", WIN_SILL, WIN_HEAD
            openings.append({
                "type": otype, "wall": kind, "width": round(wid, 3),
                "p0": [round(p0[0], 4), round(p0[1], 4)],
                "p1": [round(p1[0], 4), round(p1[1], 4)],
                "mid": [round(mid[0], 3), round(mid[1], 3)],
                "dx": round(float(dx), 5), "dz": round(float(dz), 5),
                "sill": sill, "head": head,
                "rooms": rs, "thickness": th,
            })

    bytype = defaultdict(list)
    for o in openings:
        bytype[o["type"]].append(o["width"])
    print("openings: %d" % len(openings))
    for t, ws in bytype.items():
        print("  %-12s n=%2d  width min %.2f max %.2f" % (t, len(ws), min(ws), max(ws)))

    print("\nlist:")
    for o in sorted(openings, key=lambda o: -o["width"]):
        print("  %-12s w=%5.2f  at (%7.2f,%7.2f)  %s" %
              (o["type"], o["width"], o["mid"][0], o["mid"][1], "/".join(o["rooms"])))

    json.dump({"openings": openings, "door_h": DOOR_H,
               "win": [WIN_SILL, WIN_HEAD], "glaze": [GLAZE_SILL, GLAZE_HEAD]},
              open(os.path.join(RAW, "openings.json"), "w"), ensure_ascii=False, indent=1)
    print("\nwrote raw/openings.json")


if __name__ == "__main__":
    main()