"""BART: sprites, direction names and the data provider for arrivals_board.

Copy to the root of CIRCUITPY next to code.py, bart.py, feeds.py, arrivals_board.py
and gtsr4.pem. BART publishes JSON, so the GTFS-Realtime decoder is not needed.
"""
import ssl

import adafruit_connection_manager
import adafruit_requests
import wifi

import bart
import feeds

NAME = "BART"
SHEET = "/img/bart_sheet.bmp"
BULLETS = {"RED": 0, "ORANGE": 1, "BLUE": 2, "GREEN": 3, "YELLOW": 4, "GREY": 5}
FALLBACK_TILE = 7       # neutral ring: unknown line, no service, errors
ALERT_TILE = 6
BLANK_TILE = 15
ARROWS = ("/img/train_NORTH.bmp", "/img/train_SOUTH.bmp", 39)
LABEL_X = (15, 40)
DIRECTIONS = ("North", "South")
DUE_TEXT = "Due"        # BART reports this as "Leaving"
REFRESH = 15            # seconds; BART regenerates its estimates roughly every 15 s
ALERT_REFRESH = 120     # seconds between service advisory fetches
ADVISORY_MAX_AGE_MS = 1800000
NIGHT_HOURS = (20, 6)   # every text label is red from 20:00 to 06:00
STARTUP_TILES = (8, 9)  # lowercase b over a train nose until the first fetch
ROOT_CERT_PATH = "/gtsr4.pem"  # GTS Root R4, the root api.bart.gov's certificate chains to; see README
FETCH_TIMEOUT = 10


class Provider:
    """Fetches BART's real-time departures straight from api.bart.gov."""

    def __init__(self, secrets, network, profile=False):
        self.network = network
        self.profile = profile
        self.station = (secrets.get("bart_station") or "").strip().upper()
        feeds.require(self.station, "bart_station must be set, e.g. 16TH")
        self.key = (secrets.get("bart_key") or "").strip() or bart.PUBLIC_KEY
        self.lines = bart.parse_lines(secrets.get("bart_lines"))
        unknown = (self.lines or set()) - set(bart.KNOWN_COLORS)
        feeds.require(not unknown, "unknown BART line(s) {}; use {}".format(",".join(sorted(unknown)), ",".join(bart.KNOWN_COLORS)))
        self.default_direction = feeds.pick_direction(secrets.get("default_direction"), DIRECTIONS)
        self.etd_url = bart.etd_url(self.station, self.key)
        self.bsa_url = bart.bsa_url(self.key)
        self.headers = feeds.plain_headers()
        self.pool = None
        self.root_cert = None
        self.sessions = []
        self.preferred = None  # session_id that last worked; tried first after a reset
        self.stamps = {}
        self.advisories = feeds.Cached("BART advisories", self._fetch_advisories, ADVISORY_MAX_AGE_MS, [], on_error=self.reset)

    # ------------------------------------------------------------- sessions
    def _open_sessions(self):
        """One session trusting the shipped GTS Root R4 (CircuitPython 10.3's bundle lacks the
        root BART's chain is anchored to) and one using the firmware bundle as a fallback."""
        self.network.connect()
        if self.pool is None:
            self.pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
        root_cert = None
        try:
            with open(ROOT_CERT_PATH) as cert_file:
                root_cert = cert_file.read()
        except OSError:
            print("No {} on the board; using the firmware certificate bundle only".format(ROOT_CERT_PATH))
        if root_cert is not None and "BEGIN CERTIFICATE" not in root_cert:
            # an empty cadata would silently disable certificate checking, so refuse it
            print("{} is not a PEM certificate; using the firmware certificate bundle only".format(ROOT_CERT_PATH))
            root_cert = None
        sessions = []
        if root_cert:
            self.root_cert = root_cert  # keep the text referenced for as long as the context uses it
            context = ssl.create_default_context()
            context.load_verify_locations(cadata=root_cert)
            sessions.append(("bart-root", adafruit_requests.Session(self.pool, context, session_id="bart-root")))
        sessions.append(("bart-bundle", adafruit_requests.Session(self.pool, ssl.create_default_context(), session_id="bart-bundle")))
        if self.preferred:
            sessions.sort(key=lambda item: 0 if item[0] == self.preferred else 1)
        self.sessions = sessions

    def _fetch_json(self, url, label):
        """GET and parse JSON, trying each TLS session until one connects."""
        if not self.sessions:
            self._open_sessions()
        last_error = None
        for index, (name, session) in enumerate(self.sessions):
            try:
                response = session.get(url, headers=self.headers, timeout=FETCH_TIMEOUT)
            except (OSError, RuntimeError, adafruit_requests.OutOfRetries) as e:
                last_error = e  # socket or TLS trouble: try the next session
                continue
            try:
                content_type = response.headers.get("content-type", "")
                if "json" not in content_type:
                    # a Cloudflare challenge or outage page arrives as text/html
                    raise feeds.FeedError("HTTP {} {} from {}".format(response.status_code, content_type, label))
                data = response.json()
            finally:
                response.close()
            error = bart.api_error(data)
            if error:
                raise feeds.FeedError(error)
            if response.status_code != 200:
                raise feeds.FeedError("HTTP {} from {}".format(response.status_code, label))
            if index:
                self.sessions.insert(0, self.sessions.pop(index))
            self.preferred = name
            return data
        raise last_error

    # ----------------------------------------------------------------- data
    def _fetch_advisories(self):
        started = feeds.now_ms()
        advisories = bart.parse_bsa(self._fetch_json(self.bsa_url, "advisories"))
        if self.profile:
            print("PROFILE advisories: fetched and parsed in {} ms mem_free {}".format(feeds.now_ms() - started, feeds.mem_free()))
        return advisories

    def refresh_alerts(self):
        self.advisories.refresh()

    def fetch(self):
        started = feeds.now_ms()
        etd = self._fetch_json(self.etd_url, "departures")
        root = etd.get("root", {})
        feeds.check_feed(self.stamps, "etd", root.get("date", "") + " " + root.get("time", ""))
        if self.profile:
            print("PROFILE etd: fetched and parsed in {} ms mem_free {}".format(feeds.now_ms() - started, feeds.mem_free()))
        return bart.build_arrivals(etd, self.advisories.current(), self.lines)

    def reset(self):
        feeds.reset_connections(self.pool, getattr(self.network, "requests", None))  # PortalBase shares the pool
        self.sessions = []
