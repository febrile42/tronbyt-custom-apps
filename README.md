# tronbyt-custom-apps

Apps served to a Tronbyt server via the per-user **custom apps repository**
setting (`app_repo_url`). The server clones this repo and scans `apps/<name>/`,
so the layout mirrors [tronbyt/apps](https://github.com/tronbyt/apps).

This exists to run an app on real hardware *before* it is merged upstream.

## apps/mbta

MBTA departures, ahead of upstream. Currently carries the changes in
[tronbyt/apps#646](https://github.com/tronbyt/apps/pull/646) and
[tronbyt/apps#648](https://github.com/tronbyt/apps/pull/648):

- Fixes the stop picker failing with "Error loading options" when the location
  comes from the device record rather than a fresh search-box pick. The server
  supplies `lat`/`lng` as JSON numbers there, and the runtime requires strings.
- Shows the real per-trip headsign instead of the route's terminus. At
  Main St @ Briggs St, consecutive 137 buses run to Oak Grove and to Malden;
  both previously read "MALDEN CENTER STATION".
- Excludes CANCELLED trips, which were shown as live departures.
- Adds a route filter at stops served by more than one route.
- Fixes the Mattapan badge rendering as an empty circle.

Once those PRs merge, delete `apps/mbta` here so the system app takes over
again. Two copies of the same app id will otherwise both appear in the picker.
