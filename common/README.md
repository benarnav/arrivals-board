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

`tests/test_gtfsrt.py` covers the wire primitives (varints, every wire type, chunk
boundaries, truncation, extension skipping, translation selection) and compares the decoder
with Google's `gtfs-realtime-bindings` on captured feeds through `fixtures/snapshots.json`.
Beyond the committed fixtures, the decoder was checked against Google's library on every MTA
feed (8 feeds, up to 138 KB and 3,717 stop rows), the WMATA feed (2,591 rows), the BART feed
and the full 450 KB MTA alerts feed (181 alerts): identical output on all of them. The
snapshot tests also pass under the MicroPython unix port, which shares CircuitPython's
interpreter design.