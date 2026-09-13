"""Washington Metrorail: sprites, direction names and the data provider for arrivals_board.

Copy to the root of CIRCUITPY next to code.py, wmata.py, gtfsrt.py, feeds.py and
arrivals_board.py. Needs CircuitPython 10 or newer: its certificate bundle includes
the root api.wmata.com's certificate chains to, which 9.2 lacked.
"""
import feeds
import gtfsrt
import wmata

NAME = "WMATA"
SHEET = "/img/wmata-sheet.bmp"
BULLETS = {"RED": 0, "ORANGE": 1, "BLUE": 2, "GREEN": 3, "YELLOW": 4, "SILVER": 5}
FALLBACK_TILE = 7       # the WMATA tile: unknown line, no service, errors
ALERT_TILE = 6
BLANK_TILE = 15
ARROWS = ("/img/train_NE.bmp", "/img/train_SW.bmp", 28)
LABEL_X = (13, 39)
DIRECTIONS = ("NE", "SW")
DUE_TEXT = "ARR"
REFRESH = 15            # seconds; WMATA regenerates its feed every ~5 s, the key allows 50,000 calls a day
ALERT_REFRESH = 120     # seconds between incident fetches
INCIDENT_MAX_AGE_MS = 1800000
NIGHT_HOURS = None
STARTUP_TILES = None
PLATFORM_SUFFIXES = ("1", "2", "C")  # every platform id in the feed is PF_<station>_<suffix>


class Provider:
    """Fetches and decodes WMATA's GTFS-Realtime trip updates and Incidents JSON on the board."""

    def __init__(self, secrets, network, profile=False):
        self.network = network
        self.profile = profile
        self.key = (secrets.get("wmata_key") or "").strip()
        feeds.require(self.key, "wmata_key must be set (https://developer.wmata.com)")
        self.station_ids = wmata.parse_list(secrets.get("station_ids"))
        feeds.require(self.station_ids, "station_ids must be set, e.g. A01,C01")
        self.lines_config = wmata.parse_list(secrets.get("lines"))  # empty means every line serving the station
        unknown = self.lines_config - set(wmata.LINES)
        feeds.require(not unknown, "unknown WMATA line(s) {}; use {}".format(",".join(sorted(unknown)), ",".join(wmata.LINES)))
        self.default_direction = feeds.pick_direction(secrets.get("default_direction"), DIRECTIONS)
        self.stop_ids = set("PF_{}_{}".format(code, suffix) for code in self.station_ids for suffix in PLATFORM_SUFFIXES)
        # the JSON call must not ask for gzip: adafruit_requests cannot parse a gzipped JSON body
        self.json_headers = feeds.plain_headers()
        self.json_headers["api_key"] = self.key
        self.headers = feeds.gzip_headers()
        self.headers["api_key"] = self.key
        self.stamps = {}
        self.incidents = feeds.Cached("WMATA incidents", self._fetch_incidents, INCIDENT_MAX_AGE_MS, None, on_error=self.reset)

    def _decode_trips(self, source):
        return gtfsrt.decode_trip_updates(source, self.lines_config or set(wmata.LINES), self.stop_ids)

    def _fetch_incidents(self):
        started = feeds.now_ms()
        data = self.network.fetch_data(wmata.INCIDENTS_URL, json_path=[], headers=self.json_headers)
        if not isinstance(data, dict):
            raise feeds.FeedError("unexpected incidents response")
        if self.profile:
            print("PROFILE incidents: fetched and parsed in {} ms mem_free {}".format(feeds.now_ms() - started, feeds.mem_free()))
        return data

    def refresh_alerts(self):
        self.incidents.refresh()

    def fetch(self):
        timestamp, rows = feeds.fetch_gtfsrt(self.network, wmata.TRIPS_URL, self._decode_trips, self.headers,
                                             "rail trip updates", self.profile)
        feeds.check_feed(self.stamps, "rail trip updates", timestamp)
        # incidents are scoped to the configured lines, or to the lines actually serving the station
        lines = self.lines_config or wmata.station_lines(rows, self.station_ids) or set(wmata.LINES)
        data = self.incidents.current()
        texts, alerted = wmata.parse_incidents(data, lines) if data else ([], set())
        return wmata.build_arrivals(timestamp, rows, self.station_ids, self.lines_config or None, alerted, texts)

    def reset(self):
        feeds.reset_connections(session=getattr(self.network, "requests", None))
