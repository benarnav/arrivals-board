"""Minimal GTFS-Realtime decoder for CircuitPython.

Reads the protobuf wire format directly (no protobuf library) and keeps only
what an arrivals board needs, so a 100 KB feed costs a few kilobytes of RAM:
each FeedEntity is decoded from its own small buffer, trips for unwanted routes
are skipped as soon as their route is known, and only stop-time updates for the
wanted stops are kept.

Sources can be a byte string (for example a gzip-decoded body) or any iterable
of byte chunks such as ``response.iter_content(512)`` from adafruit_requests.

Field numbers from https://gtfs.org/documentation/realtime/proto/:
  FeedMessage      header=1 entity=2
  FeedHeader       timestamp=3
  FeedEntity       trip_update=3 alert=5
  TripUpdate       trip=1 stop_time_update=2
  TripDescriptor   trip_id=1 route_id=5 direction_id=6
  StopTimeUpdate   arrival=2 departure=3 stop_id=4
  StopTimeEvent    time=2
  Alert            active_period=1 informed_entity=5 header_text=10
  TimeRange        start=1 end=2
  EntitySelector   route_id=2
  TranslatedString translation=1 -> Translation text=1 language=2
Anything else (including agency extensions such as MTA's field 1001) is skipped
by wire type.
"""

_WT_VARINT = 0
_WT_64BIT = 1
_WT_LENGTH = 2
_WT_32BIT = 5


class StreamReader:
    """Byte reader over an iterable of chunks (a file, or Response.iter_content)."""

    def __init__(self, chunks):
        self._chunks = iter(chunks)
        self._buf = b""
        self._pos = 0
        self._eof = False

    def read(self, size):
        """Exactly ``size`` bytes, or fewer only at end of input."""
        if len(self._buf) - self._pos < size and not self._eof:
            parts = [self._buf[self._pos:]]
            have = len(parts[0])
            while have < size:
                try:
                    chunk = next(self._chunks)
                except StopIteration:
                    chunk = b""
                if not chunk:
                    self._eof = True
                    break
                parts.append(chunk)
                have += len(chunk)
            self._buf = b"".join(parts)
            self._pos = 0
        out = self._buf[self._pos:self._pos + size]
        self._pos += len(out)
        return out

    def read_varint(self):
        """Next varint, or None at end of input."""
        result = 0
        shift = 0
        while True:
            byte = self.read(1)
            if not byte:
                if shift:
                    raise ValueError("truncated varint")
                return None
            value = byte[0]
            result |= (value & 0x7F) << shift
            if value < 0x80:
                return result
            shift += 7
            if shift > 63:
                raise ValueError("varint too long")


class BytesReader:
    """Byte reader over an in-memory buffer.

    Each read copies one top-level field (an entity of a few hundred bytes) into a
    bytes object: on CircuitPython, parsing bytes is markedly faster than parsing
    a memoryview, and the copy is small."""

    def __init__(self, data):
        self._data = data if isinstance(data, bytes) else bytes(data)
        self._pos = 0

    def read(self, size):
        out = self._data[self._pos:self._pos + size]
        self._pos += len(out)
        return out

    def read_varint(self):
        data = self._data
        pos = self._pos
        if pos >= len(data):
            return None
        result = 0
        shift = 0
        while True:
            if pos >= len(data):
                raise ValueError("truncated varint")
            value = data[pos]
            pos += 1
            result |= (value & 0x7F) << shift
            if value < 0x80:
                self._pos = pos
                return result
            shift += 7
            if shift > 63:
                raise ValueError("varint too long")


def make_reader(source):
    """BytesReader for bytes-like sources, StreamReader for anything iterable."""
    if isinstance(source, (bytes, bytearray, memoryview)):
        return BytesReader(source)
    return StreamReader(source)


def varint(buf, pos):
    """Decode a varint at ``pos``; returns (value, next_pos)."""
    result = 0
    shift = 0
    end = len(buf)
    while True:
        if pos >= end:
            raise ValueError("truncated varint")
        value = buf[pos]
        pos += 1
        result |= (value & 0x7F) << shift
        if value < 0x80:
            return result, pos
        shift += 7
        if shift > 63:
            raise ValueError("varint too long")


def skip(buf, pos, wire_type, end=None):
    """Skip one field value of ``wire_type`` starting at ``pos``; ``end`` bounds the message."""
    if end is None:
        end = len(buf)
    if wire_type == _WT_VARINT:
        return varint(buf, pos)[1]
    if wire_type == _WT_LENGTH:
        length, pos = varint(buf, pos)
        return _bounded(pos, length, end)
    if wire_type == _WT_64BIT:
        return _bounded(pos, 8, end)
    if wire_type == _WT_32BIT:
        return _bounded(pos, 4, end)
    raise ValueError("bad wire type %d" % wire_type)


def _bounded(pos, length, end):
    """End of a field of ``length`` bytes at ``pos``, or ValueError if it overruns the message."""
    if pos + length > end:
        raise ValueError("truncated message")
    return pos + length


def _text(buf, pos, length):
    return buf[pos:pos + length].decode()


def _encode_all(values):
    """A set of str as a set of bytes, so feed strings can be matched without decoding them."""
    if values is None:
        return None
    return set(value.encode() for value in values)


def _stop_needles(stops):
    """Wire bytes of a StopTimeUpdate.stop_id field per wanted stop: tag 0x22, length, id.

    A trip whose bytes contain none of them cannot stop at a wanted stop, so it can be
    skipped without scanning its stop-time updates. None when a stop id is too long
    for a one-byte length (never the case for real ids).
    """
    if stops is None:
        return None
    needles = []
    for stop in stops:
        if len(stop) >= 128:
            return None
        needles.append(b"\x22" + bytes([len(stop)]) + stop)
    return needles


def iter_top_level(reader):
    """Yield (field_number, payload) for each length-delimited top-level field.

    Raises ValueError if the input ends in the middle of a field.
    """
    while True:
        tag = reader.read_varint()
        if tag is None:
            return
        field = tag >> 3
        wire_type = tag & 7
        if wire_type == _WT_LENGTH:
            length = reader.read_varint()
            if length is None:
                raise ValueError("truncated feed")
            payload = reader.read(length)
            if len(payload) != length:
                raise ValueError("truncated feed")
            yield field, payload
        elif wire_type == _WT_VARINT:
            if reader.read_varint() is None:
                raise ValueError("truncated feed")
        elif wire_type == _WT_64BIT:
            reader.read(8)
        elif wire_type == _WT_32BIT:
            reader.read(4)
        else:
            raise ValueError("bad wire type %d" % wire_type)


def header_timestamp(buf):
    """FeedHeader.timestamp, or None when absent."""
    pos = 0
    end = len(buf)
    timestamp = None
    while pos < end:
        tag, pos = varint(buf, pos)
        if tag == (3 << 3) | _WT_VARINT:
            timestamp, pos = varint(buf, pos)
        else:
            pos = skip(buf, pos, tag & 7, end)
    return timestamp


# ---------------------------------------------------------------- trip updates

def _stop_time_event(buf, pos, end):
    """StopTimeEvent -> time (or None)."""
    value = None
    while pos < end:
        tag, pos = varint(buf, pos)
        if tag == (2 << 3) | _WT_VARINT:
            value, pos = varint(buf, pos)
        else:
            pos = skip(buf, pos, tag & 7, end)
    return value


def _stop_time_update(buf, pos, end, stops):
    """StopTimeUpdate -> (stop_id bytes, arrival_time, departure_time, wanted).

    The event sub-messages are only decoded when the stop is one of ``stops``
    (or ``stops`` is None); other stops just cost the field scan.
    """
    stop_id = None
    arrival_span = None
    departure_span = None
    while pos < end:
        tag = buf[pos]
        pos += 1
        if tag >= 0x80:
            tag, pos = varint(buf, pos - 1)
        field = tag >> 3
        wire_type = tag & 7
        if wire_type == _WT_LENGTH:
            length, pos = varint(buf, pos)
            stop = _bounded(pos, length, end)
            if field == 4:
                stop_id = buf[pos:stop]
            elif field == 2:
                arrival_span = (pos, stop)
            elif field == 3:
                departure_span = (pos, stop)
            pos = stop
        else:
            pos = skip(buf, pos, wire_type, end)
    if stop_id is None or (stops is not None and stop_id not in stops):
        return stop_id, None, None, False
    arrival = _stop_time_event(buf, arrival_span[0], arrival_span[1]) if arrival_span else None
    departure = _stop_time_event(buf, departure_span[0], departure_span[1]) if departure_span else None
    return stop_id, arrival, departure, True


def _trip_descriptor(buf, pos, end):
    """TripDescriptor -> (trip_id bytes, route_id bytes, direction_id)."""
    trip_id = None
    route_id = None
    direction_id = None
    while pos < end:
        tag, pos = varint(buf, pos)
        field = tag >> 3
        wire_type = tag & 7
        if wire_type == _WT_LENGTH:
            length, pos = varint(buf, pos)
            stop = _bounded(pos, length, end)
            if field == 1:
                trip_id = buf[pos:stop]
            elif field == 5:
                route_id = buf[pos:stop]
            pos = stop
        elif field == 6 and wire_type == _WT_VARINT:
            direction_id, pos = varint(buf, pos)
        else:
            pos = skip(buf, pos, wire_type, end)
    return trip_id, route_id, direction_id


def _trip_entity(buf, routes, stops, needles, rows):
    """Decode one FeedEntity; append matching stop rows to ``rows``."""
    pos = 0
    end = len(buf)
    while pos < end:
        tag, pos = varint(buf, pos)
        field = tag >> 3
        wire_type = tag & 7
        if field == 3 and wire_type == _WT_LENGTH:
            length, pos = varint(buf, pos)
            stop = _bounded(pos, length, end)
            _trip_update(buf, pos, stop, routes, stops, needles, rows)
            pos = stop
        else:
            pos = skip(buf, pos, wire_type, end)


def _has_wanted_stop(buf, pos, end, needles):
    for needle in needles:
        if buf.find(needle, pos, end) >= 0:
            return True
    return False


def _trip_update(buf, pos, end, routes, stops, needles, rows):
    if needles is not None and not _has_wanted_stop(buf, pos, end, needles):
        return  # none of the wanted stops appear anywhere in this trip
    trip_id = None
    route_id = None
    direction_id = None
    last_stop = None
    found = []
    while pos < end:
        tag = buf[pos]
        pos += 1
        if tag >= 0x80:
            tag, pos = varint(buf, pos - 1)
        field = tag >> 3
        wire_type = tag & 7
        if wire_type != _WT_LENGTH:
            pos = skip(buf, pos, wire_type, end)
            continue
        length, pos = varint(buf, pos)
        stop = _bounded(pos, length, end)
        if field == 1:
            trip_id, route_id, direction_id = _trip_descriptor(buf, pos, stop)
            if routes is not None and route_id not in routes:
                return  # not a line we show: skip the rest of this trip
        elif field == 2:
            stop_id, arrival, departure, wanted = _stop_time_update(buf, pos, stop, stops)
            if stop_id is not None:
                last_stop = stop_id
                if wanted:
                    found.append((stop_id, arrival, departure))
        pos = stop
    if routes is not None and route_id not in routes:
        return
    if not found:
        return
    route_text = route_id.decode() if route_id is not None else None
    trip_text = trip_id.decode() if trip_id is not None else None
    last_text = last_stop.decode() if last_stop is not None else None
    for stop_id, arrival, departure in found:
        rows.append((route_text, direction_id, trip_text, stop_id.decode(), arrival, departure, last_text))


def decode_trip_updates(source, routes=None, stops=None):
    """Decode a TripUpdates feed.

    ``routes`` and ``stops`` are sets of route_id / stop_id strings to keep
    (None keeps everything). Returns (header_timestamp, rows) where each row is
    (route_id, direction_id, trip_id, stop_id, arrival_time, departure_time, last_stop_id)
    and times are Unix seconds (None when the feed omitted them).
    """
    reader = make_reader(source)
    routes = _encode_all(routes)
    stops = _encode_all(stops)
    needles = _stop_needles(stops)
    timestamp = None
    rows = []
    for field, payload in iter_top_level(reader):
        if field == 2:
            _trip_entity(payload, routes, stops, needles, rows)
        elif field == 1:
            timestamp = header_timestamp(payload)
    return timestamp, rows


# ---------------------------------------------------------------------- alerts

def _time_range(buf, pos, end):
    start = 0
    stop = 0
    while pos < end:
        tag, pos = varint(buf, pos)
        if tag == (1 << 3) | _WT_VARINT:
            start, pos = varint(buf, pos)
        elif tag == (2 << 3) | _WT_VARINT:
            stop, pos = varint(buf, pos)
        else:
            pos = skip(buf, pos, tag & 7, end)
    return start, stop


def _entity_selector_route(buf, pos, end):
    route_id = None
    while pos < end:
        tag, pos = varint(buf, pos)
        field = tag >> 3
        wire_type = tag & 7
        if wire_type == _WT_LENGTH:
            length, pos = varint(buf, pos)
            stop = _bounded(pos, length, end)
            if field == 2:
                route_id = _text(buf, pos, length)
            pos = stop
        else:
            pos = skip(buf, pos, wire_type, end)
    return route_id


def _translated_string(buf, pos, end, language="en"):
    """First translation in ``language`` (or the first translation at all)."""
    chosen = None
    fallback = None
    while pos < end:
        tag, pos = varint(buf, pos)
        field = tag >> 3
        wire_type = tag & 7
        if field == 1 and wire_type == _WT_LENGTH:
            length, pos = varint(buf, pos)
            stop = _bounded(pos, length, end)
            text, lang = _translation(buf, pos, stop)
            pos = stop
            if fallback is None:
                fallback = text
            if lang == language and chosen is None:
                chosen = text
        else:
            pos = skip(buf, pos, wire_type, end)
    return chosen if chosen is not None else fallback


def _translation(buf, pos, end):
    text = ""
    lang = None
    while pos < end:
        tag, pos = varint(buf, pos)
        field = tag >> 3
        wire_type = tag & 7
        if wire_type == _WT_LENGTH:
            length, pos = varint(buf, pos)
            stop = _bounded(pos, length, end)
            if field == 1:
                text = _text(buf, pos, length)
            elif field == 2:
                lang = _text(buf, pos, length)
            pos = stop
        else:
            pos = skip(buf, pos, wire_type, end)
    return text, lang


def _alert_entity(buf, routes, alerts):
    pos = 0
    end = len(buf)
    while pos < end:
        tag, pos = varint(buf, pos)
        field = tag >> 3
        wire_type = tag & 7
        if field == 5 and wire_type == _WT_LENGTH:
            length, pos = varint(buf, pos)
            stop = _bounded(pos, length, end)
            _alert(buf, pos, stop, routes, alerts)
            pos = stop
        else:
            pos = skip(buf, pos, wire_type, end)


def _alert(buf, pos, end, routes, alerts):
    periods = []
    alert_routes = set()
    header_pos = None
    header_end = None
    while pos < end:
        tag, pos = varint(buf, pos)
        field = tag >> 3
        wire_type = tag & 7
        if wire_type != _WT_LENGTH:
            pos = skip(buf, pos, wire_type, end)
            continue
        length, pos = varint(buf, pos)
        stop = _bounded(pos, length, end)
        if field == 1:
            periods.append(_time_range(buf, pos, stop))
        elif field == 5:
            route_id = _entity_selector_route(buf, pos, stop)
            if route_id:
                alert_routes.add(route_id)
        elif field == 10:
            header_pos = pos
            header_end = stop
        pos = stop
    if routes is not None and not (alert_routes & routes):
        return
    text = _translated_string(buf, header_pos, header_end) if header_pos is not None else ""
    alerts.append((alert_routes, periods, text or ""))


def decode_alerts(source, routes=None):
    """Decode an Alerts feed.

    Returns (header_timestamp, alerts); each alert is
    (set_of_route_ids, [(start, end), ...], header_text) with 0 meaning an
    open-ended period bound. Only alerts naming a route in ``routes`` are kept
    when ``routes`` is given.
    """
    reader = make_reader(source)
    timestamp = None
    alerts = []
    for field, payload in iter_top_level(reader):
        if field == 2:
            _alert_entity(payload, routes, alerts)
        elif field == 1:
            timestamp = header_timestamp(payload)
    return timestamp, alerts


def is_active(periods, now):
    """True when ``now`` falls in any period; an alert with no periods is always active."""
    if not periods:
        return True
    for start, end in periods:
        if start <= now and (end == 0 or now <= end):
            return True
    return False
