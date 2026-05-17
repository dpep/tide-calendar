# SF Bay tide-current calendars

Publishes Google Calendar feeds of NOAA tidal-current predictions — slack
water, max ebb, and max flood — for SF Bay stations. A daily GitHub Action
regenerates the `.ics` files; GitHub Pages serves them; Google Calendar
subscribes to the URLs.

## How it works

1. `generate.py` reads `stations.yaml` and, for each station, fetches the NOAA
   CO-OPS `currents_predictions` product (`MAX_SLACK` interval).
2. It writes one `docs/<slug>.ics` per station, a combined `docs/all.ics`, and
   an `docs/index.html` listing all feeds.
3. The GitHub Action runs daily, commits any changes under `docs/`, and Pages
   serves them.

## Setup

1. Create a GitHub repo and push this directory:
   ```
   gh repo create tide-calendar --public --source=. --push
   ```
2. Repo **Settings → Pages**: set source to branch `master`, folder `/docs`.
3. Repo **Settings → Actions → General → Workflow permissions**: enable
   *Read and write permissions* (lets the Action commit regenerated feeds).
4. Run the workflow once (**Actions → Update tide calendars → Run workflow**),
   or run `python generate.py` locally and commit `docs/`.
5. Open `https://<you>.github.io/tide-calendar/` — it lists every feed URL.

## Subscribing in Google Calendar

*Other calendars → From URL* → paste a feed URL, e.g.
`https://<you>.github.io/tide-calendar/golden-gate.ics`

Note: Google refreshes subscribed URLs on its own schedule (often 12–24h). That
is fine here — predictions are stable weeks out.

## Choosing locations

Edit `stations.yaml`. Each entry under `stations:` becomes one feed; add,
remove, or comment out entries to pick locations. `bin` selects the depth layer
(shallowest ≈ surface current).

### Common SF Bay current stations

| Station   | Location                          | Suggested bin |
|-----------|-----------------------------------|---------------|
| SFB1201   | San Francisco Bay Entrance (Outside) | 26         |
| SFB1203   | Golden Gate Bridge, 0.46 nm E     | 18            |
| SFB1204   | Alcatraz Island, southwest of     | 18            |
| SFB1207   | Bay Bridge, Pier D                | 18            |
| SFB1209   | Yerba Buena Island (midchannel)   | 23            |
| SFB1211   | Alcatraz Island, 0.5 mi north of  | 22            |
| SFB1212   | Raccoon Strait                    | 9             |
| SFB1213   | Oakland Inner Harbor Channel      | 12            |
| SFB1217   | Rincon Point                      | 16            |
| SFB1305   | San Mateo Bridge                  | 7             |
| SFB1306   | Coyote Point, 2.3 nmi NNE of      | 7             |
| SFB1309   | Point Chauncey                    | 11            |
| SFB1312   | Point San Pablo (midchannel)      | 16            |
| SFB1318   | Carquinez Bridge, I-80            | 9             |
| SFB1319   | Carquinez Strait                  | 10            |

Full, searchable list:
[NOAA Current Predictions map](https://tidesandcurrents.noaa.gov/map/index.html?type=CurrentPredictions).

## Notes

- NOAA blocks some datacenter IP ranges. If a scheduled run fails with
  `Forbidden`, run `python generate.py` locally and commit `docs/` instead, or
  switch the Action to a self-hosted runner.
- Predictions are NOAA estimates, not for navigation.
