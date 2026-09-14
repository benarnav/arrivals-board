"""Fetch plumbing shared by every city's provider (copy to the board next to code.py).

Nothing here touches the display. The parts that need CircuitPython-only modules
import them lazily or guard the import, so the module also loads on a desktop.
"""
import gc
import time

try:
    import zlib  # CircuitPython's zlib inflates gzip bodies (MTA serves them on request)
except ImportError:
    zlib = None

try:
    import adafruit_connection_manager
except ImportError:
    adafruit_connection_manager = None

USER_AGENT = "arrivals-board/2.0 (MatrixPortal S3; CircuitPython)"
CHUNK_SIZE = 4096      # bytes read from the socket at a time
FETCH_TIMEOUT = 20     # seconds; the largest feed is ~140 KB plain, 30 KB gzipped
STALE_AFTER_MS = 120000  # a feed stamp may stay unchanged this long before it counts as an outage

if hasattr(time, "monotonic_ns"):
    def now_ms():
        """Milliseconds since boot as an int; unlike time.monotonic() it stays exact for years."""
        return time.monotonic_ns() // 1000000
else:  # MicroPython unix port, used for desktop compatibility checks
    def now_ms():
        return time.ticks_ms()


class FeedError(Exception):
    """The server answered, but not with usable data (bad key, HTML page, stale feed...)."""


def require(condition, message):
    """Fail at startup with a readable message instead of showing 'No Service' forever."""
    if not condition:
        raise ValueError("secrets.py: " + message)


def pick_direction(text, directions):
    """Case-insensitive match of a secrets value against the city's direction pair."""
    wanted = (text or "").strip().lower()
    for direction in directions:
        if direction.lower() == wanted:
            return direction
    raise ValueError("secrets.py: default_direction must be one of " + ", ".join(directions))


def plain_headers():
    return {"User-Agent": USER_AGENT}


def gzip_headers():
    """Ask for gzip when the board can inflate it; servers that cannot gzip just ignore it."""
    headers = plain_headers()
    if zlib is not None:
        headers["Accept-Encoding"] = "gzip"
    return headers


def mem_free():
    return gc.mem_free() if hasattr(gc, "mem_free") else -1


def fetch_gtfsrt(network, url, decode, headers, label, profile=False):
    """GET ``url`` through PortalBase and run ``decode(source)`` on the body.

    A gzipped body is downloaded, inflated and decoded from RAM (4 to 5 times less to
    transfer); anything else streams through the decoder in CHUNK_SIZE pieces so
    memory stays flat whatever the feed size. Raises FeedError on a non-200 answer.
    """
    started = now_ms()
    downloaded = inflated = None
    size = 0
    response = network.fetch(url, headers=headers, timeout=FETCH_TIMEOUT)
    try:
        if response.status_code != 200:
            raise FeedError("HTTP {} from {}".format(response.status_code, label))
        if response.headers.get("content-encoding", "") == "gzip":
            if zlib is None:
                raise FeedError("gzip body from {} but no zlib module".format(label))
            body = b"".join(response.iter_content(CHUNK_SIZE))
            downloaded = now_ms()
            data = zlib.decompress(body, 31)
            body = None
            inflated = now_ms()
            size = len(data)
            result = decode(data)
            data = None
        else:
            size = int(response.headers.get("content-length", "0") or 0)
            result = decode(response.iter_content(CHUNK_SIZE))
    finally:
        response.close()
    if profile:
        finished = now_ms()
        if downloaded is not None:
            print("PROFILE {}: {} B gzip: download {} ms inflate {} ms decode {} ms total {} ms mem_free {}".format(
                label, size, downloaded - started, inflated - downloaded, finished - inflated, finished - started, mem_free()))
        else:
            print("PROFILE {}: {} B streamed and decoded in {} ms mem_free {}".format(label, size, finished - started, mem_free()))
    return result


def check_feed(stamps, label, stamp, stale_after_ms=STALE_AFTER_MS):
    """Raise FeedError when a feed has no stamp or its stamp has not changed for too long.

    ``stamps`` is a dict the caller keeps; ``stamp`` is whatever identifies a feed
    generation (a header timestamp, or BART's date and time strings).
    """
    if stamp is None:
        raise FeedError(label + " feed has no header")
    now = now_ms()
    previous = stamps.get(label)
    if previous and previous[0] == stamp:
        if now - previous[1] > stale_after_ms:
            raise FeedError("{} feed stuck at {} for {} s".format(label, stamp, (now - previous[1]) // 1000))
    else:
        stamps[label] = (stamp, now)


def reset_connections(pool=None, session=None):
    """Close every pooled socket so the next request reconnects cleanly.

    adafruit_requests can leave a socket registered but unusable after a failure while
    reading a response; every later request to that host then fails until it is closed.
    ``session`` is PortalBase's adafruit_requests.Session: its fetch_data never closes a
    response, and Session.request() closes the previous one before every request, which
    would raise "Socket not managed" forever once close_all has dropped that socket.
    """
    last = getattr(session, "_last_response", None)
    if last is not None:
        try:
            last.close()  # frees the socket while the manager still knows it
        except Exception:
            pass
        last.socket = None
        session._last_response = None
    if adafruit_connection_manager is None:
        return
    try:
        adafruit_connection_manager.connection_manager_close_all(pool)
    except Exception as e:
        print("closing sockets failed:", e)


def ensure_wifi(ssid, password, on_reconnect=None, timeout=10):
    """True when the radio is associated; reconnects after a drop.

    PortalBase remembers its first successful connect and never retries, and the
    firmware gives up after a few attempts, so a router reboot would otherwise leave
    the board offline until it reloads.
    """
    import wifi

    if wifi.radio.connected:
        return True
    try:
        wifi.radio.connect(ssid, password, timeout=timeout)
    except Exception as e:
        print("WiFi reconnect failed:", e)
        return False
    print("WiFi reconnected")
    if on_reconnect is not None:
        on_reconnect()
    return True


def disable_wifi_sleep():
    """The board is mains-powered; modem sleep only adds latency to every packet."""
    try:
        import wifi

        if hasattr(wifi.radio, "power_management"):
            wifi.radio.power_management = wifi.PowerManagement.NONE
    except Exception as e:
        print("could not disable WiFi power management:", e)


class Cached:
    """A value refreshed on demand: keep the last good one, drop it once it is too old.

    ``refresh()`` is called by the board in its own loop slot so a slow fetch never
    stacks on a trip fetch; ``current()`` never fetches.
    """

    def __init__(self, name, fetch, max_age_ms, default, on_error=None):
        self.name = name
        self.fetch = fetch
        self.max_age_ms = max_age_ms
        self.default = default
        self.on_error = on_error  # called after a network-level failure (not a FeedError)
        self.value = default
        self.fetched = None

    def refresh(self):
        """Fetch a new value; on failure keep the old one (until it expires)."""
        try:
            self.value = self.fetch()
            self.fetched = now_ms()
            return True
        except Exception as e:
            print(self.name, "error:", e)
            if self.on_error is not None and not isinstance(e, FeedError):
                self.on_error()  # a read that fails midway can leave the pooled socket unusable
            return False

    def current(self):
        if self.value != self.default and (self.fetched is None or now_ms() - self.fetched > self.max_age_ms):
            print("Dropping stale", self.name)
            self.value = self.default
        return self.value
