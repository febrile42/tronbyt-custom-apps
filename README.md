# tronbyt-custom-apps

Apps served to a Tronbyt server via the per-user **custom apps repository**
setting (`app_repo_url`, under "Custom Apps Repository" in user settings — not
the "System Apps Repository" field above it). The server clones this repo and
scans `apps/<name>/`, so the layout mirrors
[tronbyt/apps](https://github.com/tronbyt/apps).

This exists to run an app on real hardware *before* it is merged upstream.

## apps/nightclock

A very dim clock, for use as a night mode below the panel's hardware brightness
floor. Landed here untested as a starting point; reviewed and revised in
subsequent commits before going on hardware.
