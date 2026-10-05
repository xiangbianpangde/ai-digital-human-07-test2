#!/usr/bin/env python3
"""Draw the derived wall network and openings over the real floor plan."""
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
SRC = os.path.abspath(os.path.join(HERE, "..", "武汉104119325592-房源资料"))
PLAN = os.path.join(SRC, "02-户型图与封面", "真实户型图.jpg")

COL = {
    "门": (0, 200, 60), "阳台推拉门": (0, 160, 255), "窗": (0, 140, 255),
    "落地窗/阳台门": (255, 120, 0), "开放式门洞": (255, 0, 200),
}


def main():
    walls = json.load(open(os.path.join(RAW, "walls.json")))
    ops = json.load(open(os.path.join(RAW, "openings.json")))["openings"]
    mp = json.load(open(os.path.join(RAW, "plan_mapping.json")))
    rooms = json.load(open(os.path.join(RAW, "rooms_vr.json")))
    im = Image.open(PLAN).convert("RGB")
    d = ImageDraw.Draw(im)
    th = np.radians(mp["rotation_deg"]); ct, st = np.cos(th), np.sin(th)
    sc = mp["scale_px_per_m"]; tx, ty = mp["translate_px"]

    def px(x, z):
        return ((x * ct - z * st) * sc + tx, (x * st + z * ct) * sc + ty)

    try:
        fbig = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 26)
        fsm = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 20)
    except Exception:
        fbig = fsm = ImageFont.load_default()

    for r in rooms:
        pts = [px(*p) for p in r["pts_vr"]] + [px(*r["pts_vr"][0])]
        d.line(pts, fill=(255, 0, 0), width=2)
        c = np.mean(pts[:-1], axis=0)
        d.text((c[0] - 26, c[1]), r["name"], fill=(200, 0, 0), font=fsm,
               stroke_width=2, stroke_fill=(255, 255, 255))

    for grp, col in (("walls_interior", (0, 200, 0)), ("walls_exterior", (160, 0, 200))):
        for w in walls[grp]:
            d.line([px(*w["a"]), px(*w["b"])], fill=col, width=3)

    for o in ops:
        c = COL.get(o["type"], (255, 0, 0))
        d.line([px(*o["p0"]), px(*o["p1"])], fill=c, width=7)
        m = px(*o["mid"])
        d.text((m[0] - 18, m[1] - 12), "%s%.2f" % (o["type"][:2], o["width"]),
               fill=c, font=fsm, stroke_width=2, stroke_fill=(255, 255, 255))

    out = os.path.join(RAW, "plan_check.jpg")
    im.save(out, quality=90)
    print("wrote", out)


if __name__ == "__main__":
    main()