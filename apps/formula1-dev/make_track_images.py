#!/usr/bin/env python3
"""Regenerate the EXTRA_TRACKS images in formula1.star.

The upstream metadata feed stores each circuit as a base64 PNG: 30x24, a
one-pixel #9e9e9e centreline on black, rotated so the circuit fills the frame
rather than pointing north. This reproduces that from open geodata, so a new
circuit can be added the moment it lands on the calendar instead of waiting for
the feed.

The pipeline was validated against a tile the feed already has: rebuilding
Circuit de Barcelona-Catalunya from OpenStreetMap reproduces the published
tile's shape and orientation, and the traced lap comes to 4683 m against an
official 4657 m.

Sources and licences are in README.md. Needs only Pillow.
Writes the base64 strings to stdout.
"""

import base64
import io
import json
import math
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw

GREY = (158, 158, 158, 255)
BLACK = (0, 0, 0, 255)
WIDTH, HEIGHT, MARGIN = 30, 24, 1

# Chosen by eye against the existing tiles. A heavier stroke closes up the gap
# between Sepang's two parallel straights.
STROKE = 0.7
THRESHOLD = 60
SUPERSAMPLE = 10

OVERPASS = "https://overpass-api.de/api/interpreter"
UA = "tronbyt-formula1-dev/1.0 (track tile generator)"

SOURCES = {
    # The Madrid street circuit. OpenStreetMap has it as a route relation whose
    # members include the public-road sections, which are not tagged as raceway
    # and are missed by a naive query - that is why the lap looks fragmentary
    # unless you walk the relation.
    "madring": {"kind": "osm", "relation": 18813472, "exclude": [1552567031]},
    # Sepang has no route relation, and its raceway ways include the north and
    # south short circuits, so picking out the GP loop is guesswork. The CC0
    # diagram is unambiguous and carries no restrictions.
    "sepang": {
        "kind": "svg",
        "url": "https://upload.wikimedia.org/wikipedia/commons/3/3c/"
               "F1_circuits_2014-2018_-_Sepang_International_Circuit_%28version_2%29.svg",
        "path_id": "path4133",
        "rotate": 0,
    },
}

TOKEN = re.compile(r"([MmLlHhVvCcSsZz])|(-?\d*\.?\d+(?:[eE][-+]?\d+)?)")


def fetch(url, data=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read()


# --- OpenStreetMap -----------------------------------------------------------

def osm_lap(relation_id, exclude):
    """Walk a route=raceway relation into one closed lap of (lat, lon)."""
    query = "[out:json][timeout:90];rel(%d);out tags;(rel(%d);>>;);out geom;" % (
        relation_id, relation_id)
    data = json.loads(fetch(OVERPASS, query.encode()))
    ways = {w["id"]: w for w in data["elements"] if w["type"] == "way"}
    rel = next(e for e in data["elements"]
               if e["type"] == "relation" and e.get("members"))

    lap = []
    for member in rel["members"]:
        if member["type"] != "way" or member["ref"] in exclude:
            continue
        geom = [(g["lat"], g["lon"]) for g in ways[member["ref"]]["geometry"]]
        if member.get("role") == "backward":
            geom.reverse()
        if not lap:
            lap = geom
            continue
        # Trust the geometry over the role tag: keep whichever end connects.
        if metres(lap[-1], geom[-1]) < metres(lap[-1], geom[0]):
            geom.reverse()
        lap += geom[1:] if metres(lap[-1], geom[0]) < 1.0 else geom

    gap = metres(lap[0], lap[-1])
    if gap > 5.0:
        raise SystemExit("relation %d does not close: %.1f m gap" % (relation_id, gap))
    return lap


def metres(a, b):
    return math.hypot((a[0] - b[0]) * 111320,
                      (a[1] - b[1]) * 111320 * math.cos(math.radians(a[0])))


def lap_length(lap):
    return sum(metres(lap[i], lap[i + 1]) for i in range(len(lap) - 1))


def to_plane(lap):
    """Equirectangular projection, metres, y already screen-down."""
    lat0 = sum(p[0] for p in lap) / len(lap)
    k = math.cos(math.radians(lat0))
    return [(p[1] * k * 111320, -p[0] * 111320) for p in lap]


# --- SVG ---------------------------------------------------------------------

def _cubic(p0, p1, p2, p3, steps=16):
    out = []
    for i in range(1, steps + 1):
        t = i / steps
        u = 1 - t
        out.append((u*u*u*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t*t*t*p3[0],
                    u*u*u*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t*t*t*p3[1]))
    return out


def svg_path(url, path_id):
    root = ET.fromstring(fetch(url))
    node = next(e for e in root.iter() if e.get("id") == path_id)
    toks = [("cmd", m.group(1)) if m.group(1) else ("num", float(m.group(2)))
            for m in TOKEN.finditer(node.get("d"))]
    i, pts, x, y, cmd, prev = 0, [], 0.0, 0.0, None, None
    start = (0.0, 0.0)

    def take(n):
        nonlocal i
        vals = [toks[i + k][1] for k in range(n)]
        i += n
        return vals

    while i < len(toks):
        if toks[i][0] == "cmd":
            cmd = toks[i][1]
            i += 1
            if cmd in "Zz":
                x, y = start
                continue
        rel, base = cmd.islower(), cmd.upper()
        if base == "M":
            dx, dy = take(2)
            x, y = (x + dx, y + dy) if rel else (dx, dy)
            pts.append((x, y))
            start = (x, y)
            cmd = "l" if rel else "L"
            prev = None
        elif base == "L":
            dx, dy = take(2)
            x, y = (x + dx, y + dy) if rel else (dx, dy)
            pts.append((x, y))
            prev = None
        elif base == "H":
            (dx,) = take(1)
            x = x + dx if rel else dx
            pts.append((x, y))
            prev = None
        elif base == "V":
            (dy,) = take(1)
            y = y + dy if rel else dy
            pts.append((x, y))
            prev = None
        elif base in "CS":
            if base == "C":
                ax, ay, bx, by, ex, ey = take(6)
                p1 = (x + ax, y + ay) if rel else (ax, ay)
            else:
                bx, by, ex, ey = take(4)
                p1 = (2 * x - prev[0], 2 * y - prev[1]) if prev else (x, y)
            p2 = (x + bx, y + by) if rel else (bx, by)
            p3 = (x + ex, y + ey) if rel else (ex, ey)
            pts += _cubic((x, y), p1, p2, p3)
            prev, x, y = p2, p3[0], p3[1]
        else:
            raise NotImplementedError("SVG command %r" % cmd)
    return pts


# --- rendering ---------------------------------------------------------------

def rotate(plane, degrees):
    a = math.radians(degrees)
    ca, sa = math.cos(a), math.sin(a)
    return [(x * ca - y * sa, x * sa + y * ca) for x, y in plane]


def frame_fit(plane):
    xs = [p[0] for p in plane]
    ys = [p[1] for p in plane]
    span_x = (max(xs) - min(xs)) or 1e-9
    span_y = (max(ys) - min(ys)) or 1e-9
    return min((WIDTH - 2 * MARGIN) / span_x, (HEIGHT - 2 * MARGIN) / span_y)


def best_rotation(plane):
    """The angle that lets the circuit fill the tile.

    Purely functional: it maximises drawn size, nothing else. On Catalunya it
    picks the same orientation the published tile uses.
    """
    return max(range(180), key=lambda d: frame_fit(rotate(plane, d)))


def tile(plane):
    xs = [p[0] for p in plane]
    ys = [p[1] for p in plane]
    min_x, min_y = min(xs), min(ys)
    span_x = (max(xs) - min_x) or 1e-9
    span_y = (max(ys) - min_y) or 1e-9
    box_w, box_h = WIDTH - 2 * MARGIN, HEIGHT - 2 * MARGIN
    scale = min(box_w / span_x, box_h / span_y)
    off_x = MARGIN + (box_w - span_x * scale) / 2
    off_y = MARGIN + (box_h - span_y * scale) / 2

    s = SUPERSAMPLE
    big = Image.new("RGBA", (WIDTH * s, HEIGHT * s), BLACK)
    line = [(((x - min_x) * scale + off_x) * s, ((y - min_y) * scale + off_y) * s)
            for x, y in plane]
    if line[0] != line[-1]:
        line.append(line[0])
    ImageDraw.Draw(big).line(line, fill=GREY, width=max(1, int(s * STROKE)),
                             joint="curve")

    small = big.resize((WIDTH, HEIGHT), Image.LANCZOS)
    out = Image.new("RGBA", (WIDTH, HEIGHT), BLACK)
    src, dst = small.load(), out.load()
    for py in range(HEIGHT):
        for px in range(WIDTH):
            r, g, b, _ = src[px, py]
            if (r + g + b) / 3 > THRESHOLD:
                dst[px, py] = GREY
    return out


def main():
    for circuit, spec in SOURCES.items():
        if spec["kind"] == "osm":
            lap = osm_lap(spec["relation"], spec.get("exclude", []))
            plane = to_plane(lap)
            print("# %s: %d points, lap %.0f m" % (circuit, len(lap), lap_length(lap)),
                  file=sys.stderr)
        else:
            plane = svg_path(spec["url"], spec["path_id"])
        degrees = spec.get("rotate")
        if degrees is None:
            degrees = best_rotation(plane)
            print("# %s: rotated %d deg to fill the tile" % (circuit, degrees),
                  file=sys.stderr)
        image = tile(rotate(plane, degrees))
        buf = io.BytesIO()
        image.save(buf, format="PNG", optimize=True)
        print('    "%s": "%s",' % (circuit, base64.b64encode(buf.getvalue()).decode()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
