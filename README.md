# tronbyt-custom-apps

Apps served to a Tronbyt server via the per-user **custom apps repository**
setting (`app_repo_url`, under "Custom Apps Repository" in user settings — not
the "System Apps Repository" field above it). The server clones this repo and
scans `apps/<name>/`, so the layout mirrors
[tronbyt/apps](https://github.com/tronbyt/apps).

This exists to run an app on real hardware *before* it is merged upstream.

## apps/mbta-dev

MBTA departures, ahead of upstream. Tracks the changes in
[tronbyt/apps#646](https://github.com/tronbyt/apps/pull/646) and
[tronbyt/apps#648](https://github.com/tronbyt/apps/pull/648):

- Fixes the stop picker failing with "Error loading options" when the location
  comes from the device record rather than a fresh search-box pick. The server
  supplies `lat`/`lng` as JSON numbers there, and the runtime requires strings.
- Shows the real per-trip headsign instead of the route's terminus. At
  North Ave @ Church St, consecutive 137 buses run to Oak Grove and to Malden;
  both previously read "MALDEN CENTER STATION".
- Excludes CANCELLED trips, which were shown as live departures.
- Disambiguates same-named stops. The two stops on opposite sides of a street
  share one name, so "Main St @ Water St" appeared twice with
  nothing to tell them apart. Stops now read e.g. "Main St @ Water St
  (to Reading Depot)".
- Folds the route into the stop list, so picking a stop picks the route and
  direction together. This replaces a `schema.Generated` dropdown that never
  rendered on a real server.
- Keeps the configured stop selectable when the settings page is reopened. The
  page rebuilds the list from the *device's* location, not the one that was
  searched, and reselects the saved stop only on an exact match, so a stop
  outside the device's radius silently reverted to the nearest one.
- Passes the configured API key to the stop lookups. They previously went out
  keyless against a 20 request/minute limit, and building the list takes about
  nine, so two settings loads in a minute started returning 429.
- Documents the location field: search by street address or coordinates, since
  a town name centres on the town and only stops within about a mile are listed.
- Fixes the Mattapan badge rendering as an empty circle.

### Why the id is `mbta-dev` and not `mbta`

The app picker builds its thumbnail URL as `/preview/app/{id}`, keyed on the
manifest id alone. While this app declared `id: mbta` it collided with the
built-in app of the same id, and the picker showed **upstream's** screenshot
next to our entry — which made a working install look like it had not updated.

So the manifest here deliberately differs from the pull request by three lines
(`id`, `name`, `summary`). **Do not upstream those.** The PR must keep
`id: mbta`.

### When the PRs merge

Delete `apps/mbta-dev` from this repo and install the built-in `mbta` app
instead. Leaving both installed means two apps doing the same job.
