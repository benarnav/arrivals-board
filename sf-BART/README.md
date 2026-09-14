# Arrivals Board for BART (San Francisco Bay Area)

BART publishes its predictions as small JSON documents (2 to 5 KB per station), so no GTFS-Realtime decoder is needed: the board fetches and filters them itself. Everything else (clock, weather, AQI, the two screens,
the buttons) works exactly like the NYC and DC versions described in the
[main README](../README.md).

## Files

| File | Purpose |
|---|---|
| `code.py` | Three lines: starts the shared program with this city. |
| `city.py` | BART's sprites, direction names, night hours, startup tiles and the provider that talks to api.bart.gov. |
| `bart.py` | Turns BART's JSON into the arrivals the display shows. |
| `secrets_template.py` | Fill in, save as `secrets.py`, copy to the root. |
| `gtsr4.pem` | Root certificate for `api.bart.gov` (see below). |
| `img/` | Line bullets, direction arrows, AQI icons. |

The display program itself is [common/arrivals_board.py](../common/arrivals_board.py) with
[common/feeds.py](../common/feeds.py); fonts and libraries are the same as the other cities.

## Setup

1. Prepare the MatrixPortal S3, CircuitPython and the libraries as in the main README, and
   create the Adafruit IO, OpenWeather and IQAir accounts described there. No account is
   needed for BART: the template ships with BART's public key. Registering your own free key
   at https://api.bart.gov/api/register.aspx keeps you working if the public key is ever
   rotated and gets you BART's change notices by email.
2. Fill in `secrets_template.py` and save it as `secrets.py`.
3. From the repository root run `python3 pack.py sf-BART` and copy the contents of
   `dist/sf-BART/` plus `secrets.py` to the root of the CIRCUITPY drive.

### BART settings in `secrets.py`

- `bart_station`: the four-letter station abbreviation. `12TH 16TH 19TH 24TH ANTC ASHB BALB BAYF
  BERY CAST CIVC COLS COLM CONC DALY DBRK DUBL DELN PLZA EMBR FRMT FTVL GLEN HAYW LAFY LAKE MCAR
  MLBR MLPT MONT NBRK NCON OAKL ORIN PITT PCTR PHIL POWL RICH ROCK SBRN SFIA SANL SHAY SSAN UCTY
  WCRK WARM WDUB WOAK` (also at https://api.bart.gov/docs/overview/abbrev.aspx). The Oakland
  Airport connector (`OAKL`) publishes no real-time data.
- `bart_lines`: which lines to show, by color, comma separated (`"RED,YELLOW"`). Leave empty
  to show every line serving the station. Colors: `RED ORANGE BLUE GREEN YELLOW GREY`.
- `default_direction`: `North` or `South` (checked at startup). These are BART's own route labels, not compass
  directions. Every line has one "North" end: Antioch (Yellow), Richmond (Red and Orange),
  Dublin/Pleasanton (Blue) and Berryessa for the Green line only. So a Berryessa-bound Orange
  train is "South" while a Berryessa-bound Green train is "North". In San Francisco, North is
  the platform toward downtown and the East Bay.

## What the display shows

- Until the first fetch completes the two bullets show a lowercase b over a train nose.
- Minutes are BART's estimated departure times. `Due` is BART's `Leaving` (under a minute).
- The `UP` button shows the next four trains in both directions, as in the other cities.
- A bullet flashes the alert symbol when a BART service advisory names that line, or when
  the train itself is running five or more minutes late. The `DOWN` button scrolls the
  advisory text and silences the flashing until a new advisory appears or another line is late.
  Advisories are system-wide messages, refreshed every two minutes and dropped if they cannot
  be refreshed for 30 minutes; departures refresh every 15 seconds, which is how often BART
  regenerates them.
- Cancelled trains are dropped. Red and Green trains stop running around 9 pm; after the
  last train the board shows `No Service` for that direction.
- From 20:00 to 06:00 local time every text label (clock, temperature, AQI number, minutes,
  advisory text) is drawn in red; the line bullets and the AQI icon keep their colors. The
  hours are `NIGHT_HOURS` in `city.py`, and the rule only applies once the clock has synced.

## Certificates: why `gtsr4.pem` is there

`api.bart.gov` is served through Cloudflare with a Google Trust Services certificate whose
chain is anchored, as presented to the board, at a root that CircuitPython 10.3.0 no longer
ships in its bundle (`GlobalSign Root CA`; earlier releases such as 9.2.x and 10.2.x still have
it). `city.py` therefore opens its BART connection with the shipped `GTS Root R4` root
certificate, which validates the chain on every CircuitPython release, and falls back to the
firmware's bundle if that ever stops working. If the file is missing or not a certificate the
board says so on the serial console and uses the bundle only. `gtsr4.pem` is Google's published root from
https://pki.goog/repo/certs/gtsr4.pem (SHA-256 fingerprint
`349DFA4058C5E263123B398AE795573C4E1313C83FE68F93556CD5E8031B3C7D`). Weather and AQI keep
using the firmware bundle.

## Notes on the data

BART's Legacy API `etd` command and its GTFS-Realtime feed carry the same predictions; a
side-by-side check of both feeds across every station agreed on 99.7% of estimates, with per-train
delays identical. BART labels the API "legacy" and points developers at GTFS-RT, but has not
announced a retirement. If that happens, `bart.py` and the `Provider` in `city.py` are the only files that need
changing: `arrivals_board.py` only consumes the dictionary they build.
