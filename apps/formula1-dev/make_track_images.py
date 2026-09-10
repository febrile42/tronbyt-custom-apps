#!/usr/bin/env python3
"""Regenerate the EXTRA_TRACKS images in formula1.star.

The upstream metadata feed stores each circuit as a base64 PNG: 30x24, a
one-pixel #9e9e9e centreline on black. This traces the same shape from a
published circuit diagram so a new circuit can be added the moment it lands on
the calendar, rather than waiting for the feed. Sources and licences are in
README.md.

Needs only Pillow. Writes the base64 strings to stdout.
"""

import base64
import io
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw

GREY = (158, 158, 158, 255)
BLACK = (0, 0, 0, 255)
WIDTH, HEIGHT, MARGIN = 30, 24, 1

# Chosen by eye against the existing tiles. A heavier stroke closes up the gap
# between Sepang's two parallel straights and blurs Madrid's east loop.
STROKE = 0.7
THRESHOLD = 60
SUPERSAMPLE = 10

SOURCES = {
    # circuitId: (svg url, id of the path holding the circuit outline)
    "madring": (
        "https://upload.wikimedia.org/wikipedia/commons/2/25/Madring_%282026%29.svg",
        "path1",
    ),
    "sepang": (
        "https://upload.wikimedia.org/wikipedia/commons/3/3c/"
        "F1_circuits_2014-2018_-_Sepang_International_Circuit_%28version_2%29.svg",
        "path4133",
    ),
}

TOKEN = re.compile(r"([MmLlHhVvCcSsZz])|(-?\d*\.?\d+(?:[eE][-+]?\d+)?)")


def _cubic(p0, p1, p2, p3, steps=16):
    out = []
    for i in range(1, steps + 1):
        t = i / steps
        u = 1 - t
        out.append(
            (
                u * u * u * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t * t * t * p3[0],
                u * u * u * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t * t * t * p3[1],
            )
        )
    return out


def flatten(d):
    """Turn an SVG path's `d` attribute into a list of points."""
    toks = [("cmd", m.group(1)) if m.group(1) else ("num", float(m.group(2)))
            for m in TOKEN.finditer(d)]
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


def tile(pts):
    """Fit points to the 30x24 frame and draw them in the feed's two colours."""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    span_x = max(xs) - min(xs)
    span_y = max(ys) - min(ys)
    box_w, box_h = WIDTH - 2 * MARGIN, HEIGHT - 2 * MARGIN
    scale = min(box_w / span_x, box_h / span_y)
    off_x = MARGIN + (box_w - span_x * scale) / 2
    off_y = MARGIN + (box_h - span_y * scale) / 2

    s = SUPERSAMPLE
    big = Image.new("RGBA", (WIDTH * s, HEIGHT * s), BLACK)
    line = [(((x - min(xs)) * scale + off_x) * s, ((y - min(ys)) * scale + off_y) * s)
            for x, y in zip(xs, ys)]
    line.append(line[0])
    ImageDraw.Draw(big).line(line, fill=GREY, width=max(1, int(s * STROKE)), joint="curve")

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
    for circuit, (url, path_id) in SOURCES.items():
        req = urllib.request.Request(url, headers={"User-Agent": "tronbyt-formula1-dev/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            svg = resp.read()
        root = ET.fromstring(svg)
        node = next(e for e in root.iter() if e.get("id") == path_id)
        image = tile(flatten(node.get("d")))
        buf = io.BytesIO()
        image.save(buf, format="PNG", optimize=True)
        print('    "%s": "%s",' % (circuit, base64.b64encode(buf.getvalue()).decode()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
