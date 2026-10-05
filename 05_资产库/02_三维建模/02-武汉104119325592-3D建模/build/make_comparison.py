#!/usr/bin/env python3
"""Fidelity sheet: the model's own top view beside the real floor plan with
the model's wall / door / window lines drawn on top of it.

Both panels are built independently and cropped to the building block, so the
two views line up one-to-one.
"""
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SRC = os.path.join(ROOT, "武汉104119325592-房源资料")
PLAN = os.path.join(SRC, "02-户型图与封面", "真实户型图.jpg")
TOP = os.path.join(ROOT, "renders", "02_正俯视_对照户型图.png")
OUT = os.path.join(ROOT, "renders", "04_模型与真实户型图比对.jpg")

PAD = 26
BAR = 56
GAP = 34


def font(sz):
    for p in ("/System/Library/Fonts/STHeiti Medium.ttc",
              "/System/Library/Fonts/Hiragino Sans GB.ttc"):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def main():
    rooms = json.load(open(os.path.join(RAW, "rooms_vr.json")))
    walls = json.load(open(os.path.join(RAW, "walls.json")))
    ops = json.load(open(os.path.join(RAW, "openings.json")))["openings"]
    mp = json.load(open(os.path.join(RAW, "plan_mapping.json")))

    xs = [p[0] for r in rooms for p in r["pts_vr"]]
    zs = [p[1] for r in rooms for p in r["pts_vr"]]
    spanx = max(xs) - min(xs)
    spanz = max(zs) - min(zs)
    mx, mz = (min(xs) + max(xs)) / 2, (min(zs) + max(zs)) / 2

    top = Image.open(TOP).convert("RGB")
    n = top.size[0]
    sc_px = n / (max(spanx, spanz) * 1.04)      # render px per metre
    PANW = int(round(spanx * sc_px)) + 2 * PAD
    PANH = int(round(spanz * sc_px)) + 2 * PAD

    # ---- left panel: crop the render to the building block ----
    c = n / 2.0
    L = int(round(c - (PANW / 2.0) / sc_px))
    R = int(round(c + (PANW / 2.0) / sc_px))
    T = int(round(c - (PANH / 2.0) / sc_px))
    B = int(round(c + (PANH / 2.0) / sc_px))
    panel_l = top.crop((L, T, R, B)).resize((PANW, PANH), Image.LANCZOS)

    # ---- right panel: plan cropped to the same block, in plan pixels ----
    th = np.radians(mp["rotation_deg"]); ct, st = np.cos(th), np.sin(th)
    sc = mp["scale_px_per_m"]; tx, ty = mp["translate_px"]

    def planpx(x, z):
        rx = x * ct - z * st
        rz = x * st + z * ct
        return rx * sc + tx, rz * sc + ty

    plan = Image.open(PLAN).convert("RGB")
    pw, ph = plan.size
    corners = [planpx(x, z) for x in (min(xs), max(xs)) for z in (min(zs), max(zs))]
    pxs = [p[0] for p in corners]; pzs = [p[1] for p in corners]
    marg = 0.35 * sc
    bx0 = int(min(pxs) - marg); bx1 = int(max(pxs) + marg)
    by0 = int(min(pzs) - marg); by1 = int(max(pzs) + marg)
    bx0 = max(0, bx0); by0 = max(0, by0)
    bx1 = min(pw, bx1); by1 = min(ph, by1)
    plan_crop = plan.crop((bx0, by0, bx1, by1))
    k = min(PANW / plan_crop.width, PANH / plan_crop.height)
    plan_crop = plan_crop.resize((max(1, int(plan_crop.width * k)),
                                  max(1, int(plan_crop.height * k))), Image.LANCZOS)
    panel_r = Image.new("RGB", (PANW, PANH), (255, 255, 255))
    ox = (PANW - plan_crop.width) // 2
    oy = (PANH - plan_crop.height) // 2
    panel_r.paste(plan_crop, (ox, oy))

    def S(x, z):
        p = planpx(x, z)
        return (ox + (p[0] - bx0) * k, oy + (p[1] - by0) * k)

    d = ImageDraw.Draw(panel_r)
    for r in rooms:
        pts = [S(*p) for p in r["pts_vr"]] + [S(*r["pts_vr"][0])]
        d.line(pts, fill=(225, 0, 0), width=3)
        ctr = np.mean(pts[:-1], axis=0)
        d.text((ctr[0] - 22, ctr[1] - 9), r["name"], fill=(190, 0, 0),
               font=font(17), stroke_width=3, stroke_fill=(255, 255, 255))
    for grp, col in (("walls_interior", (0, 165, 0)), ("walls_exterior", (150, 0, 200))):
        for w in walls[grp]:
            d.line([S(*w["a"]), S(*w["b"])], fill=col, width=2)
    for o in ops:
        d.line([S(*o["p0"]), S(*o["p1"])], fill=(0, 105, 255), width=6)

    # ---- compose ----
    W = PANW * 2 + GAP
    sheet = Image.new("RGB", (W, PANH + BAR), (244, 244, 247))
    sheet.paste(panel_l, (0, BAR))
    sheet.paste(panel_r, (PANW + GAP, BAR))
    dt = ImageDraw.Draw(sheet)
    dt.text((PAD, 16), "3D 模型正俯视（Blender 渲染）", fill=(20, 20, 20), font=font(28))
    dt.text((PANW + GAP + PAD, 16), "真实户型图 + 模型提取的墙体（紫/绿）与门窗（蓝）",
            fill=(20, 20, 20), font=font(28))

    sheet.save(OUT, quality=92)
    print("wrote", OUT, sheet.size)


if __name__ == "__main__":
    main()