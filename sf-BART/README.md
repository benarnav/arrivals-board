# Arrivals Board for BART (San Francisco Bay Area)

The BART version talks to BART's real-time API directly from the MatrixPortal. There is no
`Flask` proxy and no PythonAnywhere account: BART publishes its predictions as small JSON
documents (2 to 5 KB per station), so the board fetches and filters them itself. Everything
else (clock, weather, AQI, the two screens, the buttons) works exactly like the NYC and DC
versions described in the [main README](../README.md).

## Files

| File | Purpose |
|---|---|
| `code.py` | The display program. Copy to the root of the CIRCUITPY drive. |
| `bart.py` | Turns BART's JSON into the arrivals the display shows. Copy to the root next to `code.py`. |
| `secrets_template.py` | Fill in, rename to `secrets.py`, copy to the root. |
| `gtsr4.pem` | Root certificate for `api.bart.gov` (see below). Copy to the root. |
| `img/` | Line bullets, direction arrows, AQI icons. Copy the folder to the root. |
| `tests/` | Desktop tests for `bart.py`; not needed on the board. |

Fonts and libraries are the same as the other cities: copy the repository's `fonts` folder
and install the library list from the main README (`adafruit_requests` and
`adafruit_connection_manager` are already on it).

## Setup

1. Prepare the MatrixPortal S3 and CircuitPython as in the main README.
2. Weather and AQI keys as in the main README. No account is needed for BART: the file ships
   with BART's public key. Registering your own free key at
   https://api.bart.gov/api/register.aspx keeps you working if the public key is ever rotated
   and gets you BART's change notices by email.
3. Fill in `secrets_template.py`, rename it `secrets.py`, and copy it to the root.
4. Copy `code.py`, `bart.py`, `gtsr4.pem`, the `img` folder and the repository `fonts` folder to
   the root of the CIRCUITPY drive.

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
  advisory text and silences the flashing until the advisories or the flagged trains change.
  Advisories are system-wide messages, refreshed every two minutes and dropped if they cannot
  be refreshed for 30 minutes; departures refresh every 15 seconds, which is how often BART
  regenerates them.
- Cancelled trains are dropped. Red and Green trains stop running around 9 pm; after the
  last train the board shows `No Service` for that direction.
- From 20:00 to 06:00 local time every text label (clock, temperature, AQI number, minutes,
  advisory text) is drawn in red; the line bullets and the AQI icon keep their colors. The
  hours are the `NIGHT_START` and `NIGHT_END` constants at the top of `code.py`. This uses
  the board clock, so until the hourly time sync has succeeded the text may be red.

## Certificates: why `gtsr4.pem` is there

`api.bart.gov` is served through Cloudflare with a Google Trust Services certificate whose
chain is anchored, as presented to the board, at a root that CircuitPython 10.3.0 no longer
ships in its bundle (`GlobalSign Root CA`; earlier releases such as 9.2.x and 10.2.x still have
it). `code.py` therefore opens its BART connection with the shipped `GTS Root R4` root
certificate, which validates the chain on every CircuitPython release, and falls back to the
firmware's bundle if that ever stops working. If the file is missing or not a certificate the
board says so on the serial console and uses the bundle only. `gtsr4.pem` is Google's published root from
https://pki.goog/repo/certs/gtsr4.pem (SHA-256 fingerprint
`349DFA4058C5E263123B398AE795573C4E1313C83FE68F93556CD5E8031B3C7D`). Weather and AQI keep
using the firmware bundle.

## Tests

```bash
python3 -m unittest discover -s sf-BART/tests
```

The fixtures are real API responses captured on 2026-09-11 and 2026-09-12 (16th St Mission,
Embarcadero, a station with no data, a bad key, and advisories present and absent).

## Notes on the data

BART's Legacy API `etd` command and its GTFS-Realtime feed carry the same predictions; a
side-by-side check of both feeds across every station agreed on 99.7% of estimates, with per-train
delays identical. BART labels the API "legacy" and points developers at GTFS-RT, but has not
announced a retirement. If that happens, `bart.py` is the only file that needs a replacement:
`code.py` only consumes the dictionary it builds.
