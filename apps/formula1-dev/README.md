# Formula 1 (dev build)

A patched copy of the upstream `formula1` app. Temporary: delete this once the
fix is upstream and the metadata feed carries both track images.

## Why this exists

The app froze on the 6 Sep 2026 race (Monza) and stayed there. It was not a
caching problem. Every render was failing:

```
formula1.star:133: Error: key "madring" not in dict
```

The app draws the circuit outline by indexing a hand-curated `tracks.json`:

```starlark
render.Image(src = base64.decode(tracks[next_race["Circuit"]["circuitId"].lower()]), ...)
```

The 2026 Spanish Grand Prix moved to the new Madrid circuit, `madring`, which
is not in that file. A missing key fails the whole render, and a failed render
leaves the device showing whatever it drew last. The schedule feed itself was
fine: it flipped to round 14 at `2026-09-06T21:19Z`, right after Monza, which
is exactly when the display stopped moving.

Two circuits on the 2026 calendar have no image:

| round | date | circuit |
|-------|------------|-----------|
| 14 | 2026-09-13 | `madring` |
| 16 | 2026-10-04 | `sepang` |

## What is patched

1. **Missing images no longer fail the render.** `tracks.get()` instead of a
   direct index, falling back to centring the date, time and round. When the
   image is present the output is byte-identical to upstream. This part is also
   on the `f1-missing-track-image` branch of the apps fork.
2. **`EXTRA_TRACKS`** supplies the two missing images locally, so the circuit
   map still draws, merged over whatever the feed returns. The feed wins for
   every other circuit, and it wins for these two as soon as they are added
   upstream, because `EXTRA_TRACKS` only fills gaps it is asked to fill.

## Track image provenance

Both images are traced from open geodata and encoded to match the feed's own
format: 30x24 PNG, `#9e9e9e` on black, rotated so the circuit fills the frame
rather than pointing north. `make_track_images.py` regenerates them.

| circuit | source | licence | obligation |
|---------|--------|---------|------------|
| `madring` | [OpenStreetMap](https://www.openstreetmap.org/relation/18813472) relation 18813472 | ODbL 1.0 | attribution |
| `sepang` | [F1 circuits 2014-2018 - Sepang International Circuit (version 2).svg](https://commons.wikimedia.org/wiki/File:F1_circuits_2014-2018_-_Sepang_International_Circuit_(version_2).svg) by Firkin | CC0 | none |

Map data © OpenStreetMap contributors, available under the
[Open Database Licence](https://opendatacommons.org/licenses/odbl/). The tile is
an ODbL "Produced Work", so it carries an attribution requirement but **not**
share-alike; it does not oblige anything about the licence of this repository.
The Sepang image is public domain; Firkin is credited as a courtesy.

Madring is a street circuit, so most of the lap runs on ordinary public roads
that are not tagged `highway=raceway`. Querying for raceway ways alone returns a
fragmentary shape with gaps of 120 m and 700 m. The `route=raceway` relation
lists all 24 member ways in order with `forward`/`backward` roles, and walking
it in that order closes the lap exactly, every join at 0.0 m.

## Checking the pipeline

The tracing is verified two ways rather than eyeballed.

**Against a tile the feed already has.** Rebuilding Circuit de
Barcelona-Catalunya from OpenStreetMap through the same code reproduces the
published tile's shape and orientation. That is what established the feed's
convention: the tiles are rotated to fill the frame, not drawn north-up.

**Against the published lap distance.** The traced laps come out at 5448 m for
Madring against an official 5474 m, and 4683 m for Catalunya against an official
4657 m. Both within 0.5%, which is about what the difference between a
centreline and a measured racing line should be.

The rotation is chosen by maximising drawn size in the tile, a purely functional
criterion with no reference to any published diagram. On Catalunya it
independently picks the orientation the feed already uses, and on Madring it
picks the orientation the circuit is conventionally drawn in.
