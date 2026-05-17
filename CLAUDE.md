# tide-calendar

Publishes Google Calendar (`.ics`) feeds of NOAA tidal-current predictions —
slack water, max ebb, max flood — for SF Bay stations.

## Layout

- `generate.py` — fetches NOAA data and writes the `.ics` feeds. Pure stdlib
  plus PyYAML; no other dependencies.
- `stations.yaml` — the config and the only file most changes touch. One entry
  per published feed.
- `docs/` — generated output, committed and served by GitHub Pages. Do not
  hand-edit; `generate.py` overwrites it.
- `.github/workflows/update.yml` — daily regeneration + commit.

## Data source

NOAA CO-OPS `currents_predictions` product, `MAX_SLACK` interval, requested in
GMT. Endpoint: `https://api.tidesandcurrents.noaa.gov/api/datagetter`. Feeds
emit UTC timestamps (`...Z`); calendar clients render them in the viewer's
local zone.

## Conventions

- Events are zero-duration points (`DTSTART`, no `DTEND`) and `TRANSP:TRANSPARENT`
  so they never mark the user busy.
- `UID` is `{station}-{utc-timestamp}-{type}@tides.dpepper.net` — stable across
  runs so calendar clients update rather than duplicate events.
- iCalendar text is escaped and folded per RFC 5545 (`esc`, `fold`).
- `generate.py` exits non-zero if any station fails, so a broken run is loud.

## Working on this repo

- Test changes with `python generate.py` and inspect `docs/`.
- NOAA blocks some datacenter IP ranges with HTTP 403 `Forbidden`. If a fetch
  fails that way, it is an IP block, not a code bug — run from a residential
  network to verify.
- Keep `generate.py` dependency-light; do not add an iCalendar library.
- Adding a location is a `stations.yaml` edit only — no code change needed.
