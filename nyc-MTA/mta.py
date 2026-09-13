"""NYC Subway data layer: turns decoded MTA GTFS-Realtime feeds into the dictionary
code.py displays. No network or display imports, so it also runs on a desktop
for the tests in tests/.

MTA publishes one TripUpdates feed per group of lines and one Alerts feed for
the whole subway; none of them need an API key (https://api.mta.info/).
"""

FEED_BASE = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2F"
ALERTS_URL = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Fsubway-alerts"

# feed name -> route_ids carried in it (FS/GS/H are the Franklin Av, 42 St and Rockaway shuttles)
FEEDS = {
    "gtfs-ace": ("A", "C", "E", "H", "FS"),
    "gtfs-bdfm": ("B", "D", "F", "M"),
    "gtfs-g": ("G",),
    "gtfs-jz": ("J", "Z"),
    "gtfs-nqrw": ("N", "Q", "R", "W"),
    "gtfs-l": ("L",),
    "gtfs": ("1", "2", "3", "4", "5", "6", "7", "GS"),
    "gtfs-si": ("SI",),
}
DIRECTIONS = {"N": "North", "S": "South"}
MAX_TRAINS = 11        # per direction, as the old proxy returned
MAX_MINUTES = 200      # ignore predictions further out than this


def parse_list(text):
    """'A, C' -> {'A', 'C'}; empty -> empty set."""
    items = set()
    for part in (text or "").split(","):
        part = part.strip().upper()
        if part:
            items.add(part)
    return items


def feed_urls(lines):
    """URLs of every feed needed for ``lines`` (a set of route_ids), fewest first."""
    urls = []
    covered = set()
    for name, routes in FEEDS.items():
        wanted = lines & set(routes)
        if wanted:
            urls.append(FEED_BASE + name)
            covered |= wanted
    unknown = lines - covered
    if unknown:
        raise ValueError("unknown subway line(s): " + ", ".join(sorted(unknown)))
    return urls


def build_arrivals(feeds, station_ids, lines, alerted_lines=None, alert_texts=None):
    """Combine decoded feeds into {"North": [...], "South": [...], "alerts": [...]}.

    ``feeds`` is a list of (header_timestamp, rows) from gtfsrt.decode_trip_updates;
    ``station_ids`` are stop_ids with their N/S suffix (e.g. {"A41N", "A41S"}).
    Trains are sorted by minutes and capped at MAX_TRAINS per direction. Each train
    is {"Line", "Arrival", "Terminal", "Alert"} with Arrival in whole minutes and
    0 meaning "Due".
    """
    alerted_lines = alerted_lines or set()
    arrivals = {"North": [], "South": []}
    for timestamp, rows in feeds:
        if timestamp is None:
            continue
        for route_id, _direction, _trip, stop_id, arrival, departure, last_stop in rows:
            if stop_id not in station_ids or route_id not in lines:
                continue
            direction = DIRECTIONS.get(stop_id[-1:])
            if direction is None:
                continue
            when = arrival if arrival else departure
            if not when:
                continue
            minutes = (when - timestamp) / 60
            if minutes < 0 or minutes > MAX_MINUTES:
                continue
            arrivals[direction].append({
                "Line": route_id,
                "Arrival": 0 if minutes < 1.0 else _round(minutes),
                "Terminal": last_stop,
                "Alert": route_id in alerted_lines,
            })
    for direction in arrivals:
        arrivals[direction] = sorted(arrivals[direction], key=_arrival)[:MAX_TRAINS]
    arrivals["alerts"] = list(alert_texts or [])
    return arrivals


def active_alerts(alerts, lines, now):
    """Alerts from gtfsrt.decode_alerts that name one of ``lines`` and are active at ``now``.

    Returns (texts, alerted_lines): the de-duplicated header texts and the set of
    lines they name.
    """
    texts = []
    alerted = set()
    for routes, periods, text in alerts:
        matched = routes & lines
        if not matched or not _active(periods, now):
            continue
        text = " ".join(text.split())
        if text and text not in texts:
            texts.append(text)
        alerted |= matched
    return texts, alerted


def _active(periods, now):
    if not periods:
        return True
    for start, end in periods:
        if start <= now and (end == 0 or now <= end):
            return True
    return False


def _round(value):
    return int(value + 0.5)


def _arrival(train):
    return train["Arrival"]
