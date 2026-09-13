# Shared on-board decoder

`gtfsrt.py` decodes GTFS-Realtime protocol buffers on the MatrixPortal without a protobuf
library. It walks the wire format one `FeedEntity` at a time, skips trips for other routes
as soon as their route id is read, keeps only stop-time updates for the wanted stops, and
ignores unknown fields (including the MTA's extensions) by wire type. Sources can be a byte
string or any iterable of chunks such as `response.iter_content(1024)`, so a feed never has
to be held in memory when it is streamed.

The city modules (`nyc-MTA/mta.py`, `washdc-WMATA/wmata.py`) turn decoded rows into the
dictionary each `code.py` displays. `sf-BART/bart.py` does the same for BART's JSON feed.

## Correctness

The decoder was compared with Google's `gtfs-realtime-bindings` on every feed captured during
development: all eight MTA trip feeds (up to 138 KB and 3,717 stop rows), the WMATA feed
(2,591 rows), the BART feed and the full 450 KB MTA alerts feed (181 alerts), each with
several route and stop filters. Output was identical on all of them. Corrupted and truncated
feeds (2,200 fuzz cases) only ever raise ValueError. The same checks pass under the
MicroPython unix port, which shares CircuitPython's interpreter design.
