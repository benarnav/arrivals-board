"""Washington Metrorail data layer: turns WMATA's GTFS-Realtime trip updates and
its Incidents JSON into the dictionary the board displays. No network or display
imports, so it also runs on a desktop.

Both endpoints need a WMATA developer key sent as the ``api_key`` header
(https://developer.wmata.com).
"""

TRIPS_URL = "https://api.wmata.com/gtfs/rail-gtfsrt-tripupdates.pb"
INCIDENTS_URL = "https://api.wmata.com/Incidents.svc/json/Incidents"

LINES = ("RED", "ORANGE", "BLUE", "GREEN", "YELLOW", "SILVER")
LINE_CODES = {"RD": "RED", "OR": "ORANGE", "BL": "BLUE", "GR": "GREEN", "YL": "YELLOW", "SV": "SILVER"}
DIRECTIONS = {0: "NE", 1: "SW"}  # GTFS direction_id -> rough direction of travel, as the old proxy mapped it
MAX_TRAINS = 11
MAX_MINUTES = 200


def parse_list(text):
    """'blue, silver' -> {'BLUE', 'SILVER'}; empty -> empty set."""
    items = set()
    for part in (text or "").split(","):
        part = part.strip().upper()
        if part:
            items.add(part)
    return items


def station_code(stop_id):
    """'PF_A15_C' -> 'A15' (the station code used on developer.wmata.com)."""
    return stop_id[3:6]


def station_lines(rows, station_ids):
    """The Metrorail lines that actually serve ``station_ids`` according to decoded rows."""
    lines = set()
    for route_id, _direction, _trip, stop_id, _arrival, _departure, _last in rows:
        if route_id in LINES and station_code(stop_id) in station_ids:
            lines.add(route_id)
    return lines


def build_arrivals(timestamp, rows, station_ids, lines=None, alerted_lines=None, alert_texts=None):
    """{"NE": [...], "SW": [...], "alerts": [...]} from decoded trip-update rows.

    ``station_ids`` are station codes such as {"A15"}; ``lines`` limits the line
    names shown (default: every Metrorail line). Each train is
    {"Line", "Arrival", "Terminal", "Alert"}; Arrival is whole minutes, 0 = arriving.
    """
    lines = lines or set(LINES)
    alerted_lines = alerted_lines or set()
    arrivals = {"NE": [], "SW": []}
    if timestamp is not None:
        for route_id, direction_id, _trip, stop_id, arrival, departure, last_stop in rows:
            if route_id not in lines or station_code(stop_id) not in station_ids:
                continue
            direction = DIRECTIONS.get(direction_id)
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
                "Terminal": station_code(last_stop) if last_stop else None,
                "Alert": route_id in alerted_lines,
            })
    for direction in arrivals:
        arrivals[direction] = sorted(arrivals[direction], key=_arrival)[:MAX_TRAINS]
    arrivals["alerts"] = list(alert_texts or [])
    return arrivals


def parse_incidents(data, lines=None):
    """Incidents JSON -> (texts, alerted_lines) for incidents touching ``lines``."""
    lines = lines or set(LINES)
    texts = []
    alerted = set()
    for incident in data.get("Incidents", []):
        codes = incident.get("LinesAffected", "") or ""
        affected = set()
        for code in codes.replace(";", " ").split():
            name = LINE_CODES.get(code.strip().upper())
            if name:
                affected.add(name)
        matched = affected & lines
        if not matched:
            continue
        text = " ".join((incident.get("Description") or "").split())
        if text and text not in texts:
            texts.append(text)
        alerted |= matched
    return texts, alerted


def _round(value):
    return int(value + 0.5)


def _arrival(train):
    return train["Arrival"]
