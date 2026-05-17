#!/usr/bin/env python3
"""Generate iCalendar (.ics) feeds of NOAA tidal-current predictions.

For each station in stations.yaml this fetches the NOAA CO-OPS
currents_predictions product (slack water, max ebb, max flood) and writes
one .ics feed per station into docs/, ready to be served by GitHub Pages
and subscribed to from Google Calendar.

Run locally:  python generate.py
"""

import datetime as dt
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

API = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
MDAPI = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations"
ROOT = Path(__file__).parent
DOCS = ROOT / "docs"

# UID domain — only needs to be stable/unique, it is never resolved.
UID_DOMAIN = "tides.dpepper.net"

LABEL = {"slack": "Slack", "ebb": "Max Ebb", "flood": "Max Flood"}

STAMP = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def fetch(station_id, current_bin, days):
    """Return the list of current-prediction rows for a station."""
    begin = dt.date.today()
    end = begin + dt.timedelta(days=days)
    params = {
        "begin_date": begin.strftime("%Y%m%d"),
        "end_date": end.strftime("%Y%m%d"),
        "station": station_id,
        "product": "currents_predictions",
        "interval": "MAX_SLACK",  # only slack / max ebb / max flood
        "time_zone": "gmt",       # emit UTC; calendars render in local tz
        "units": "english",       # velocity in knots
        "format": "json",
        "application": "tide-calendar",
    }
    if current_bin is not None:
        params["bin"] = current_bin

    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "tide-calendar"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)

    if "current_predictions" not in data:
        msg = (data.get("error") or {}).get("message") or data.get("message")
        raise RuntimeError(msg or str(data)[:200])

    rows = data["current_predictions"].get("cp", [])
    if not rows:
        raise RuntimeError("no predictions returned")
    return rows


def station_geo(station_id):
    """Return (lat, lon) for a station from NOAA's metadata API."""
    url = f"{MDAPI}/{station_id}.json?type=currentpredictions"
    req = urllib.request.Request(url, headers={"User-Agent": "tide-calendar"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        stations = json.load(resp).get("stations", [])
    if not stations:
        raise RuntimeError("station not found in metadata API")
    return float(stations[0]["lat"]), float(stations[0]["lng"])


def events(rows):
    """Yield (utc_datetime, type, velocity_knots) for each prediction."""
    for row in rows:
        kind = (row.get("Type") or "").lower()
        if kind not in LABEL:
            continue
        when = dt.datetime.strptime(row["Time"], "%Y-%m-%d %H:%M")
        vel = row.get("Velocity_Major")
        speed = abs(float(vel)) if vel not in (None, "") else None
        yield when, kind, speed


def esc(text):
    """Escape a value for an iCalendar TEXT field (RFC 5545)."""
    return (text.replace("\\", "\\\\").replace(";", "\\;")
                .replace(",", "\\,").replace("\n", "\\n"))


def fold(line):
    """Fold a content line to <=75 octets per RFC 5545."""
    out = []
    while len(line.encode("utf-8")) > 75:
        cut = 75
        while len(line[:cut].encode("utf-8")) > 75:
            cut -= 1
        out.append(line[:cut])
        line = " " + line[cut:]
    out.append(line)
    return out


def vevent(when, kind, speed, station_id, description=None, geo=None):
    """Build one folded VEVENT block (a zero-duration point event)."""
    summary = LABEL[kind]
    if speed is not None and kind != "slack":
        summary += f": {speed:.1f} kn"

    ts = when.strftime("%Y%m%dT%H%M%SZ")
    raw = [
        "BEGIN:VEVENT",
        f"UID:{station_id}-{ts}-{kind}@{UID_DOMAIN}",
        f"DTSTAMP:{STAMP}",
        f"DTSTART:{ts}",  # no DTEND -> zero duration (RFC 5545)
        f"SUMMARY:{esc(summary)}",
    ]
    if description:
        raw.append(f"DESCRIPTION:{esc(description)}")
    if geo:
        lat, lon = geo
        raw.append(f"GEO:{lat:.5f};{lon:.5f}")
        raw.append(f"LOCATION:{esc(f'{lat:.5f}, {lon:.5f}')}")
    raw += [
        "TRANSP:TRANSPARENT",            # don't mark the user as busy
        "X-MICROSOFT-CDO-BUSYSTATUS:FREE",
        "END:VEVENT",
    ]
    folded = []
    for line in raw:
        folded += fold(line)
    return "\r\n".join(folded) + "\r\n"


def write_ics(path, calname, body):
    head = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//tide-calendar//SF Bay currents//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{esc(calname)}",
        "X-WR-TIMEZONE:America/Los_Angeles",
        "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
        "X-PUBLISHED-TTL:PT12H",
    ]
    text = "\r\n".join(head) + "\r\n" + body + "END:VCALENDAR\r\n"
    path.write_text(text, encoding="utf-8")


def write_index(feeds):
    rows = "\n".join(
        f'      <tr><td>{name}</td><td><code>{sid}</code></td>'
        f'<td>{count}</td>'
        f'<td><a href="{slug}.ics">{slug}.ics</a></td></tr>'
        for slug, name, sid, count in feeds
    )
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SF Bay Tide Calendars</title>
<style>
  body {{ font: 15px/1.5 -apple-system, sans-serif; margin: 2rem auto; max-width: 46rem; padding: 0 1rem; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
  td, th {{ border-bottom: 1px solid #ddd; padding: .4rem .6rem; text-align: left; }}
  code {{ background: #f3f3f3; padding: 0 .3rem; border-radius: 3px; }}
</style>
</head>
<body>
<h1>SF Bay tide-current calendars</h1>
<p>Slack water, max ebb, and max flood predictions from NOAA. To subscribe in
Google Calendar: <em>Other calendars &rarr; From URL</em>, and paste the full
address of an <code>.ics</code> link below (right-click &rarr; copy link).</p>
<table>
  <thead><tr><th>Location</th><th>NOAA station</th><th>Events</th><th>Feed</th></tr></thead>
  <tbody>
{rows}
  </tbody>
</table>
<p style="color:#888">Updated {STAMP}. Predictions are NOAA estimates &mdash;
not for navigation.</p>
</body>
</html>
"""
    (DOCS / "index.html").write_text(html, encoding="utf-8")


def cache_coords(fetched):
    """Write freshly-fetched {station_id: (lat, lon)} back into stations.yaml.

    Inserts `lat`/`lon` lines after the matching `id:` line so the next run
    skips the metadata lookup. Edits text directly to keep comments intact.
    """
    path = ROOT / "stations.yaml"
    out = []
    for line in path.read_text().splitlines():
        out.append(line)
        key = line.split("#", 1)[0].strip()
        for sid, (lat, lon) in fetched.items():
            if key == f"id: {sid}":
                indent = " " * (len(line) - len(line.lstrip()))
                out += [f"{indent}lat: {lat}", f"{indent}lon: {lon}"]
    path.write_text("\n".join(out) + "\n")


def main():
    cfg = yaml.safe_load((ROOT / "stations.yaml").read_text())
    days = int(cfg.get("days_ahead", 60))
    DOCS.mkdir(exist_ok=True)
    (DOCS / ".nojekyll").write_text("")  # serve files verbatim

    feeds, failures, fetched = [], [], {}
    for st in cfg["stations"]:
        slug, name, sid = st["slug"], st["name"], st["id"]
        desc = st.get("description")
        try:
            geo = (st["lat"], st["lon"]) if "lat" in st and "lon" in st else None
            if geo is None:
                geo = fetched[sid] = station_geo(sid)
            evs = list(events(fetch(sid, st.get("bin"), days)))
        except Exception as exc:  # noqa: BLE001 - report and continue
            print(f"  ! {slug}: {exc}", file=sys.stderr)
            failures.append(f"{slug} ({exc})")
            continue

        body = "".join(vevent(w, k, v, sid, desc, geo) for w, k, v in evs)
        write_ics(DOCS / f"{slug}.ics", f"SF Bay Tides — {name}", body)
        feeds.append((slug, name, sid, len(evs)))
        print(f"  ✓ {slug}: {len(evs)} events")

    if fetched:
        cache_coords(fetched)
        print(f"  cached coordinates for {len(fetched)} station(s)")

    write_index(feeds)

    if failures:
        sys.exit("FAILED: " + "; ".join(failures))


if __name__ == "__main__":
    main()
