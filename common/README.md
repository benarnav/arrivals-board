# Shared on-board code

Three modules live here. `pack.py` at the repository root copies `arrivals_board.py` and
`feeds.py` to every board and `gtfsrt.py` to the NYC and DC boards:

- `arrivals_board.py` builds the display and runs the main loop. It never knows which city
  it shows: a city module hands it sprite paths, direction names, a `Provider` class and a
  few options (`NIGHT_HOURS`, `STARTUP_TILES`). The contract is documented at the top of
  the file. Fetches are scheduled so alerts never share an iteration with a trip fetch, alerts
  scroll one at a time with fetches only in the gaps between them, WiFi drops are reconnected
  in place, and only network-level failures count toward a reload.
- `feeds.py` is the fetch plumbing the providers share: gzip-or-stream download into the
  decoder, stale-feed detection, socket reset, WiFi reconnect, millisecond timers and a
  small refresh-keep-expire cache used for alerts, incidents and advisories.
- `gtfsrt.py` decodes GTFS-Realtime protocol buffers without a protobuf library (NYC and DC
  only). It walks the wire format one `FeedEntity` at a time, skips trips for other routes
  as soon as their route id is read and trips that never mention a wanted stop after a byte
  search, keeps only the wanted stop-time updates, and ignores unknown fields (including the
  MTA's extensions) by wire type. Sources can be a byte string or any iterable of chunks such
  as `response.iter_content(4096)`, so a streamed feed never has to be held in memory.
