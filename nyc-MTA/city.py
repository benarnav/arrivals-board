"""NYC Subway: sprites, direction names and the data provider for arrivals_board.

Copy to the root of CIRCUITPY next to code.py, mta.py, gtfsrt.py, feeds.py and
arrivals_board.py. Everything the board needs to know about the MTA is here.
"""
import feeds
import gtfsrt
import mta

NAME = "MTA"
SHEET = "/img/mta_sheet.bmp"
BULLETS = {"A": 0, "C": 1, "E": 2, "B": 3, "D": 4, "F": 5, "M": 6, "G": 7, "J": 8, "Z": 9,
           "L": 10, "N": 11, "Q": 12, "R": 13, "W": 14, "S": 15, "1": 16, "2": 17, "3": 18,
           "4": 19, "5": 20, "6": 21, "7": 22, "7E": 23, "6E": 24, "SIR": 25, "FE": 28,
           # the feeds' own spellings, mapped onto the tiles above
           "SI": 25,   # Staten Island Railway
           "GS": 15,   # 42 St shuttle
           "FS": 15,   # Franklin Av shuttle
           "H": 15,    # Rockaway Park shuttle
           "6X": 24,   # <6> express
           "7X": 23}   # <7> express
FALLBACK_TILE = 27      # the MTA tile: unknown line, no service, errors
ALERT_TILE = 26
BLANK_TILE = 37
ARROWS = ("/img/train_NORTH.bmp", "/img/train_SOUTH.bmp", 39)
LABEL_X = (15, 40)
DIRECTIONS = ("North", "South")
DUE_TEXT = "Due"
REFRESH = 15            # seconds; MTA regenerates its feeds every 5 to 15 s
ALERT_REFRESH = 300     # seconds between fetches of the (large) alerts feed
ALERT_MAX_AGE_MS = 1800000
NIGHT_HOURS = None
STARTUP_TILES = None


class Provider:
    """Fetches and decodes the MTA's GTFS-Realtime feeds on the board."""

    def __init__(self, secrets, network, profile=False):
        self.network = network
        self.profile = profile
        self.station_ids = mta.parse_list(secrets.get("station_ids"))
        self.lines = mta.parse_list(secrets.get("lines"))
        feeds.require(self.station_ids and self.lines, "station_ids and lines must both be set")
        feeds.require(all(s[-1:] in ("N", "S") for s in self.station_ids),
                      "station_ids need their N or S suffix, e.g. A41N,A41S")
        self.urls = mta.feed_urls(self.lines)  # raises ValueError for unknown lines
        self.default_direction = feeds.pick_direction(secrets.get("default_direction"), DIRECTIONS)
        self.headers = feeds.gzip_headers()
        self.stamps = {}
        self.last_feed_time = None
        self.alerts = feeds.Cached("MTA alerts", self._fetch_alerts, ALERT_MAX_AGE_MS, ([], set()), on_error=self.reset)

    def _decode_trips(self, source):
        return gtfsrt.decode_trip_updates(source, self.lines, self.station_ids)

    def _decode_alerts(self, source):
        return gtfsrt.decode_alerts(source, self.lines)

    def _fetch_alerts(self):
        # streamed uncompressed on purpose: inflating the 450 KB alerts feed needs one
        # contiguous allocation the heap could not provide in testing; streaming needs a few KB
        feed_time, alerts = feeds.fetch_gtfsrt(self.network, mta.ALERTS_URL, self._decode_alerts,
                                               feeds.plain_headers(), "alerts", self.profile)
        return mta.active_alerts(alerts, self.lines, feed_time or self.last_feed_time or 0)

    def refresh_alerts(self):
        self.alerts.refresh()

    def fetch(self):
        decoded = []
        failures = []
        for url in self.urls:
            label = url.rsplit("%2F", 1)[-1]
            try:
                feed = feeds.fetch_gtfsrt(self.network, url, self._decode_trips, self.headers, label, self.profile)
                feeds.check_feed(self.stamps, label, feed[0])
                decoded.append(feed)
            except Exception as e:
                print("MTA feed", label, "failed:", e)
                failures.append(e)
        if not decoded:
            raise failures[0]  # every feed failed
        self.last_feed_time = decoded[0][0]
        texts, alerted = self.alerts.current()
        return mta.build_arrivals(decoded, self.station_ids, self.lines, alerted, texts)

    def reset(self):
        feeds.reset_connections(session=getattr(self.network, "requests", None))
