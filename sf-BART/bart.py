"""BART data layer for the arrivals board.

Turns BART Legacy API JSON (the ``etd`` real-time departures command and the
``bsa`` service advisories command) into the dictionary that the board displays:

    {"North": [train, ...], "South": [train, ...], "alerts": [text, ...]}

    train = {"Line": "RED", "Arrival": 4, "Direction": "Richmond",
             "Delay": 0, "Platform": "2", "Alert": False}

Nothing in here touches the network or the display, so the same file runs on
the MatrixPortal under CircuitPython and on a desktop.
API reference: https://api.bart.gov/docs/etd/etd.aspx and /docs/bsa/bsa.aspx
"""

PUBLIC_KEY = "MW9S-E7SL-26DU-VV8V"  # BART's published no-registration key
API_BASE = "https://api.bart.gov/api/"
DIRECTIONS = ("North", "South")
MAX_TRAINS = 11  # per direction, the same cap as the Flask proxy used for MTA and WMATA
DELAY_ALERT_SECONDS = 300  # a train running this late (etd "delay") gets the alert bullet
NO_ADVISORIES = "No advisories issued."
KNOWN_COLORS = ("RED", "ORANGE", "BLUE", "GREEN", "YELLOW", "GREY")


def etd_url(station, key=PUBLIC_KEY):
    """Real-time departures for one station (four-letter abbreviation)."""
    return API_BASE + "etd.aspx?cmd=etd&orig=" + station + "&key=" + key + "&json=y"


def bsa_url(key=PUBLIC_KEY):
    """System-wide service advisories."""
    return API_BASE + "bsa.aspx?cmd=bsa&key=" + key + "&json=y"


def parse_lines(text):
    """'red, yellow' -> {'RED', 'YELLOW'}. Empty or None -> None, meaning every line."""
    lines = set()
    for part in (text or "").split(","):
        part = part.strip().upper()
        if part:
            lines.add(part)
    return lines or None


def api_error(data):
    """The API's error text when a response carries one (bad key, bad station), else None."""
    message = data.get("root", {}).get("message")
    if isinstance(message, dict) and "error" in message:
        error = message["error"]
        if isinstance(error, dict):
            return error.get("text") or error.get("details") or "BART API error"
        return str(error)
    return None


def parse_etd(data, lines=None):
    """Parsed etd JSON -> {"North": [...], "South": [...]}, each sorted by minutes.

    Cancelled trains are dropped, "Leaving" becomes 0 minutes, and when ``lines``
    is a set of colors only those lines are kept. Raises ValueError on an API error.
    """
    error = api_error(data)
    if error:
        raise ValueError(error)
    arrivals = {"North": [], "South": []}
    for station in data["root"].get("station", []):
        for etd in station.get("etd", []):  # the key is absent when nothing is predicted
            destination = etd.get("destination", "")
            for estimate in etd.get("estimate", []):
                if estimate.get("cancelflag") == "1":
                    continue
                color = (estimate.get("color") or "").upper()
                if lines and color not in lines:
                    continue
                direction = estimate.get("direction")
                if direction not in arrivals:
                    continue
                minutes = estimate.get("minutes", "")
                if minutes == "Leaving":
                    arrival = 0
                else:
                    try:
                        arrival = int(minutes)
                    except ValueError:
                        continue
                arrivals[direction].append(
                    {
                        "Line": color,
                        "Arrival": arrival,
                        "Direction": destination,
                        "Delay": _int(estimate.get("delay")),
                        "Platform": estimate.get("platform", ""),
                        "Alert": False,
                    }
                )
    for direction in DIRECTIONS:
        arrivals[direction] = sorted(arrivals[direction], key=_arrival)[:MAX_TRAINS]
    return arrivals


def parse_bsa(data):
    """Parsed bsa JSON -> list of advisory strings, empty when BART reports none."""
    error = api_error(data)
    if error:
        raise ValueError(error)
    advisories = []
    for advisory in data["root"].get("bsa", []):
        text = _cdata(advisory.get("description"))
        if text and text != NO_ADVISORIES:
            advisories.append(text)
    return advisories


def advisory_lines(text):
    """Line colors an advisory names, e.g. 'Green Line service...' -> {'GREEN'}.

    Whole-word match so 'reduced' does not read as RED.
    """
    words = set()
    for word in text.replace("/", " ").replace("-", " ").split():
        words.add(word.strip(".,;:!?()'\"").upper())
    return {color for color in KNOWN_COLORS if color in words}


def flag_alerts(arrivals, advisories):
    """Set train["Alert"]: the train's line is named in an advisory, or it is badly late."""
    alerted = set()
    for advisory in advisories:
        alerted |= advisory_lines(advisory)
    for direction in DIRECTIONS:
        for train in arrivals.get(direction, []):
            train["Alert"] = train["Line"] in alerted or train["Delay"] >= DELAY_ALERT_SECONDS
    return arrivals


def build_arrivals(etd_data, advisories, lines=None):
    """The full dictionary code.py consumes, from parsed etd JSON and an advisory list."""
    arrivals = parse_etd(etd_data, lines)
    arrivals["alerts"] = list(advisories)
    return flag_alerts(arrivals, advisories)


def _cdata(value):
    """BART wraps text in {"#cdata-section": ...}; collapse whitespace and newlines."""
    if isinstance(value, dict):
        value = value.get("#cdata-section", "")
    return " ".join(str(value or "").split())


def _arrival(train):
    return train["Arrival"]


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
