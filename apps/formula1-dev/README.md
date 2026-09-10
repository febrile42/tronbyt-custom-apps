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

Both images were traced from published circuit diagrams and encoded to match
the feed's own format: 30x24 PNG, `#9e9e9e` on black. `make_track_images.py`
regenerates them from the source SVGs.

| circuit | source | author | licence |
|---------|--------|--------|---------|
| `madring` | [Madring (2026).svg](https://commons.wikimedia.org/wiki/File:Madring_(2026).svg) | GabrielStella | CC BY-SA 3.0 |
| `sepang` | [F1 circuits 2014-2018 - Sepang International Circuit (version 2).svg](https://commons.wikimedia.org/wiki/File:F1_circuits_2014-2018_-_Sepang_International_Circuit_(version_2).svg) | Firkin | CC0 |

The `madring` image is a derivative of a CC BY-SA 3.0 work and is offered under
[CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) on the same
terms. The `sepang` image carries no restrictions; the author is credited as a
courtesy.

Only the circuit geometry was used. None of the styling, colour, labelling or
annotation from either source appears in the output.
