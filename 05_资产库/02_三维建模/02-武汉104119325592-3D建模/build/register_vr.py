#!/usr/bin/env python3
"""Refine the SVG->VR registration with a scale fixed from the room areas,
name the 14 polygons, and render a validation overlay on the real floor plan.
"""
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
SRC = os.path.abspath(os.path.join(HERE, "..", "武汉104119325592-房源资料"))
PLAN = os.path.join(SRC, "02-户型图与封面", "真实户型图.jpg")

# polygon order after sorting by area (descending), confirmed against the plan
NAMES = [
    "客厅", "卧室B", "卧室C", "卧室A", "卧室D", "阳台C", "过道", "餐厅",
    "厨房", "阳台A", "卫生间B", "卫生间A", "阳台B", "衣帽间",
]
REAL_AREA = {
    "客厅": 24.2, "卧室B": 15.5, "卧室C": 13.2, "卧室A": 11.5, "卧室D": 8.6,
    "阳台C": 8.0, "过道": 7.4, "餐厅": 7.2, "厨房": 6.1, "阳台A": 4.3,
    "卫生间B": 4.3, "卫生间A": 4.3, "阳台B": 4.2, "衣帽间": 3.1,
}


def area_scale(rooms):
    A = np.array([r["area_units"] for r in rooms])
    R = np.array([REAL_AREA[n] for n in NAMES])
    return float(np.sqrt((A * R).sum() / (A * A).sum()))


def inside(pt, poly):
    x, y = pt
    res = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xi:
                res = not res
    return res


def containment(polys, pts):
    c = 0
    for p in pts:
        if any(inside(p, poly) for poly in polys):
            c += 1
    return c


def main():
    rooms = json.load(open(os.path.join(RAW, "rooms.json")))["rooms"]
    rooms = sorted(rooms, key=lambda r: -r["area_units"])
    work = json.load(open(os.path.join(SRC, "01-房源信息", "work.json")))
    cams = np.array([o["standing_position"] for o in work["observers"]], float)[:, [0, 2]]

    s = area_scale(rooms)
    print("scale from room areas: %.6f m/unit" % s)

    # translation: align centre of room centroids to centre of camera cloud,
    # then hill-climb on camera containment
    cent = np.array([r["centroid"] for r in rooms])
    t = cams.mean(0) - cent.mean(0) * s

    best = (-1, t[0], t[1])
    for step in (0.02, 0.01, 0.005, 0.002, 0.001):
        improved = True
        while improved:
            improved = False
            for dx in (-step, 0.0, step):
                for dy in (-step, 0.0, step):
                    cand = (best[1] + dx, best[2] + dy)
                    polys = [np.array(r["pts"]) * s + cand for r in rooms]
                    c = containment(polys, cams)
                    if c > best[0]:
                        best = (c, cand[0], cand[1])
                        improved = True
    n_in, tx, ty = best
    print("translation: (%.4f, %.4f)  -> %d/%d cameras inside" % (tx, ty, n_in, len(cams)))

    reg = {"orient": "r0", "scale_m_per_unit": s, "translate": [tx, ty],
           "cameras_inside": n_in, "cameras_total": len(cams),
           "floor_y": float(min(o["standing_position"][1] for o in work["observers"])),
           "camera_height_m": float(-min(o["standing_position"][1] for o in work["observers"]))}
    json.dump(reg, open(os.path.join(RAW, "registration.json"), "w"), indent=2)

    named = []
    for i, r in enumerate(rooms):
        poly = np.array(r["pts"]) * s + np.array([tx, ty])
        a = float(polyarea(poly))
        named.append({
            "name": NAMES[i],
            "labeled_m2": REAL_AREA[NAMES[i]],
            "measured_m2": round(a, 2),
            "pts_vr": [[round(float(x), 4), round(float(z), 4)] for x, z in poly],
        })
    json.dump(named, open(os.path.join(RAW, "rooms_vr.json"), "w"), ensure_ascii=False, indent=1)

    print("\n%-7s %8s %9s %8s" % ("room", "labeled", "measured", "diff"))
    for r in named:
        print("%-7s %8.2f %9.2f %+8.2f" % (r["name"], r["labeled_m2"], r["measured_m2"],
                                          r["measured_m2"] - r["labeled_m2"]))
    tot_m = sum(r["measured_m2"] for r in named)
    tot_l = sum(r["labeled_m2"] for r in named)
    print("%-7s %8.2f %9.2f" % ("TOTAL", tot_l, tot_m))

    # ---- validation overlay on the real floor plan ----
    im = Image.open(PLAN).convert("RGB")
    W, H = im.size
    xs = np.array([p[0] for r in named for p in r["pts_vr"]])
    ys = np.array([p[1] for r in named for p in r["pts_vr"]])
    # map plan-x -> image-x ; plan-y -> image-y (verified same handedness)
    ix0, ix1 = 380, 1560
    scale_px = (ix1 - ix0) / (xs.max() - xs.min())
    ox, oy = ix0, 130

    def to_px(x, y):
        return ((x - xs.min()) * scale_px + ox, (y - ys.min()) * scale_px + oy)

    ov = im.copy()
    d = ImageDraw.Draw(ov)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 34)
    except Exception:
        font = ImageFont.load_default()
    for r in named:
        pts = [to_px(x, y) for x, y in r["pts_vr"]]
        d.polygon(pts, fill=(0, 90, 200))
        d.line(pts + [pts[0]], fill=(220, 0, 0), width=5)
        cx = np.mean([p[0] for p in pts]); cy = np.mean([p[1] for p in pts])
        d.text((cx - 40, cy), r["name"], fill=(255, 255, 255), font=font,
               stroke_width=3, stroke_fill=(0, 0, 0))
    for o in work["observers"]:
        x, z = o["standing_position"][0], o["standing_position"][2]
        px, py = to_px(x, z)
        d.ellipse([px - 9, py - 9, px + 9, py + 9], fill=(255, 255, 0), outline=(0, 0, 0), width=2)
    ov.save(os.path.join(RAW, "overlay_check.jpg"), quality=88)
    print("\nwrote raw/overlay_check.jpg  (blue=measured room outline, yellow=cameras)")


def polyarea(p):
    a = 0.0
    n = len(p)
    for i in range(n):
        x1, y1 = p[i]
        x2, y2 = p[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


if __name__ == "__main__":
    main()