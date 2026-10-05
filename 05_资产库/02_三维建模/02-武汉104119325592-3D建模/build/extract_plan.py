#!/usr/bin/env python3
"""Extract real room geometry from the Realsee outline SVG.

Outputs build/raw/rooms.json with the 14 measured room polygons plus the
door/window line symbols recovered from the SVG.
"""
import json
import math
import os
import re
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
SVG = os.path.join(HERE, "raw", "outline.svg")
OUT = os.path.join(HERE, "raw", "rooms.json")

NUM = r"-?\d+\.?\d*(?:[eE][-+]?\d+)?"


def parse_path(d):
    """Parse M/L (absolute or relative) path data into a point list."""
    toks = re.findall(r"[MLmlZzHhVv]|-?\d+\.?\d*(?:[eE][-+]?\d+)?", d)
    pts = []
    i = 0
    cmd = None
    start = (0.0, 0.0)
    cur = (0.0, 0.0)
    while i < len(toks):
        if re.fullmatch(r"[A-Za-z]", toks[i]):
            cmd = toks[i]
            i += 1
            continue
        if cmd is None:
            break
        rel = cmd.islower()
        c = cmd.upper()
        if c in ("M", "L"):
            x, y = float(toks[i]), float(toks[i + 1])
            i += 2
            if rel:
                x, y = cur[0] + x, cur[1] + y
            cur = (x, y)
            pts.append(cur)
            if c == "M":
                start = cur
        elif c == "H":
            x = float(toks[i])
            i += 1
            cur = (cur[0] + x if rel else x, cur[1])
            pts.append(cur)
        elif c == "V":
            y = float(toks[i])
            i += 1
            cur = (cur[0], cur[1] + y if rel else y)
            pts.append(cur)
        else:
            i += 1
    return pts


def dedupe(pts, eps=1e-6):
    out = []
    for p in pts:
        if not out or abs(p[0] - out[-1][0]) > eps or abs(p[1] - out[-1][1]) > eps:
            out.append(p)
    if len(out) > 1 and abs(out[0][0] - out[-1][0]) < eps and abs(out[0][1] - out[-1][1]) < eps:
        out.pop()
    return out


def poly_area(pts):
    a = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def centroid(pts):
    a = 0.0
    cx = cy = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        cr = x1 * y2 - x2 * y1
        a += cr
        cx += (x1 + x2) * cr
        cy += (y1 + y2) * cr
    a *= 0.5
    if abs(a) < 1e-12:
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return (sum(xs) / n, sum(ys) / n)
    return (cx / (6 * a), cy / (6 * a))


def main():
    root = ET.parse(SVG).getroot()
    rooms = []
    for g in root:
        if g.tag.split("}")[-1] != "g" or g.get("type") != "areaGroup":
            continue
        for el in g:
            if el.tag.split("}")[-1] != "path" or el.get("type") != "area":
                continue
            pts = dedupe(parse_path(el.get("d")))
            if len(pts) < 3:
                continue
            rooms.append(
                {
                    "id": el.get("id"),
                    "pts": pts,
                    "area_units": poly_area(pts),
                    "centroid": centroid(pts),
                }
            )

    # door / window symbols: the lineGroup holds swung-door arcs and window bars
    symbols = []
    for g in root:
        if g.tag.split("}")[-1] != "g" or g.get("type") != "lineGroup":
            continue
        for el in g.iter():
            if el.tag.split("}")[-1] != "path":
                continue
            if el.get("type") != "line":
                continue
            pts = dedupe(parse_path(el.get("d")))
            if pts:
                symbols.append({"id": el.get("id"), "pts": pts})

    data = {"rooms": rooms, "symbols": symbols}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(data, f, ensure_ascii=False)

    print("rooms: %d, symbols: %d -> %s" % (len(rooms), len(symbols), OUT))
    for i, r in enumerate(sorted(rooms, key=lambda r: -r["area_units"])):
        xs = [p[0] for p in r["pts"]]
        ys = [p[1] for p in r["pts"]]
        print(
            "  %2d %-18s verts=%2d area=%9.1f bbox x[%7.1f,%7.1f] y[%7.1f,%7.1f]"
            % (
                i,
                str(r["id"])[:18],
                len(r["pts"]),
                r["area_units"],
                min(xs),
                max(xs),
                min(ys),
                max(ys),
            )
        )


if __name__ == "__main__":
    main()