# Arrivals Board for NYC Subway, DC Metro and BART

These files power a 64x32 RGB matrix display that shows arrival times for the New York City Subway, the Washington DC Metro Rail, or BART in the San Francisco Bay Area. Everything runs on the board: no server, no proxy. I am currently using an Adafruit Matrixportal S3 micocontroller. It was vaguely inspired by Tidbyt products, but mostly just the form factor. You can [find instructions](#setup) on how to set this up yourself at the bottom.

<img src="/example.jpg" alt="example">

## Overview

New York City has the most extensive public transportation system in the United States, but due to its age (over 100 years old!) it is frequently in need of major maintenance which disrupts or delays service. To avoid needlessly waiting for trains on the platform, this display shows the next two trains traveling in one direction (the way I'm usually going) from the station closest to my apartment. Pushing the built-in `Up` button on the microcontroller displays the next `four` trains going in both directions.

The default screen also shows the time, temperature and AQI level. The AQI icon is color coded to signal the recommendations put out by the [US gov](www.airnow.gov). The subway line icons (known as 'bullets' in official parlance), will flash an alert symbol if the transit agency has issued an alert for that line. Pushing the onboard `Down` button will scroll the alerts along the bottom of the display.

Originally, I used an Adafruit Matrixportal M4, but it doesn't have enough memory for all the information and would frequently crash. I also would like to add additional functionality, so the additional memory is necessary.
<p align="center">
<img src="/arrivals_board.gif" alt="example2">
</p>

## Note on data

The NYC Subway and Washington DC Metro publish their real-time data as GTFS-Realtime protocol buffers. Google's protobuf library does not fit on a microcontroller, so the board uses a small streaming decoder of its own, [common/gtfsrt.py](common/gtfsrt.py), that reads the wire format directly and keeps only the trips and stops it needs. The decoder's working set is a few kilobytes: WMATA's feed streams through it, and the MTA feeds are downloaded gzipped (about 30 KB) and inflated in RAM (about 140 KB) first because that is 4 to 5 times less to transfer. Earlier versions used a `Flask` proxy on PythonAnywhere for this; that is gone. The MTA feeds need no key; WMATA needs a free developer key. BART publishes a small JSON feed and is handled by [sf-BART](sf-BART/README.md). Stations and lines are set in `secrets.py`.

NYC Subway routes are organized into two travel directions: North and South and looking at a map this is fairly easy to figure out which direction you would want displayed. Washington DC's Metro is a little more complex and in the official data feed trains are listed as direction 0 or direction 1. I have mapped these to roughly trains that end in the North or East and ones that end in the South or West.

## Future Plans

I’ve been thinking about adding a dial that would allow switching between more than just two screens, but I haven’t thought of what other sort of information I’d like to display. I would also like to build a case for it.

Each decoded train carries its terminal stop id (`Terminal`), and displaying this or filtering trains based on it could be useful for users who need that level of specificity.

I’d also like to add support for other transit agencies, so if you live in a city where this would be useful, please contribute!

---

## Setup

### Hardware

These are the components I used in my build:

- Adafruit [Matrixportal S3](https://learn.adafruit.com/adafruit-matrixportal-s3/overview)
- 64x32 RGB LED Matrix display - 4mm pitch, similar to [this one](https://www.adafruit.com/product/2278)
- A [diffusion panel](https://www.adafruit.com/product/4749)
- Wall power adapter to USB C (5V 2.5A), similar to [this one](https://www.adafruit.com/product/1995). Note: the linked adapter also requires a Micro B USB to USB C [adapter](https://www.adafruit.com/product/4299). If it's out of stock, it is also [available here](https://www.digikey.com/en/products/detail/adafruit-industries-llc/1995/7902284).
- [UGLU Adhesive Dashes](https://www.amazon.com/Glu-Dashes-160/dp/B007GCRKBM/ref=sr_1_3) used to adhere the diffusion panel to the LED Matrix display. Adafruit recommended.

### Software

1. Follow the [instructions on this page](https://learn.adafruit.com/adafruit-matrixportal-s3/prep-the-matrixportal) to prepared the display and install CircuitPython. Download the [library files](https://circuitpython.org/libraries). Ensure the following are placed inside the `lib` folder when installing libraries:
    - adafruit_bitmap_font/
    - adafruit_bus_device/
    - adafruit_display_shapes/
    - adafruit_display_text/
    - adafruit_esp32spi/
    - adafruit_imageload/
    - adafruit_io/
    - adafruit_matrixportal/
    - adafruit_minimqtt/
    - adafruit_portalbase/
    - adafruit_connection_manager.mpy
    - adafruit_fakerequests.mpy
    - adafruit_lis3dh.mpy
    - adafruit_requests.mpy
    - neopixel.mpy
    - adafruit_ticks.mpy

2. If you are setting this up in Washington, DC, [sign up](https://developer.wmata.com) for a developer account and get an API key. If you are setting this up for NYC, no API key is necessary. For BART, follow [sf-BART/README.md](sf-BART/README.md).
3. Copy the `fonts` folder to the root directory on the Matrixportal.
4. Copy the `img` folder for your selected transit system to the root directory.
5. Download and fill out the fields in `secrets_template.py` for your city according to the inline instructions. NYC needs the GTFS stop ids of your station with their `N`/`S` suffix (from `stops.txt` in the [MTA GTFS zip](http://web.mta.info/developers/data/nyct/subway/google_transit.zip)) and the lines to show; DC needs the station codes from the WMATA developer portal.
6. Rename `secrets_template.py` to `secrets.py` and copy it to the root directory.
7. Copy the city's `code.py` and its data module (`nyc-MTA/mta.py` or `washdc-WMATA/wmata.py`) to the root directory, together with the shared decoder [common/gtfsrt.py](common/gtfsrt.py). DC needs CircuitPython 10 or newer: its certificate bundle includes the root `api.wmata.com` chains to, which 9.2 lacked.
8. It is best practice to use a serial monitor (Ex. from the Arduino IDE) to ensure the code is running correctly before attaching the LED Matrix display as computer supplied USB-C power is often not enough to power the board and display. This can make it appear that the code is failing when the issue may actually be insufficient power.
9. Enjoy not waiting on the platform.

## Features

If you used a Matrixportal S3, it has three buttons built into the board. From top to bottom they are: `RESET`, `UP` and `DOWN`. Here is the current functionality of each button:

- `RESET` will reset the device and will reload the code, it's useful in case the board looses its wi-fi connection or other errors.
- `UP` will change the display to show the next four trains in both directions, as seen in the example gif above.
- `DOWN` scrolls any active alerts on the lines selected during setup.

## Testing and profiling

The data layers are plain Python with no board dependencies, so they are tested on a desktop against real captured feeds:

```bash
python3 -m unittest discover -s common/tests
python3 -m unittest discover -s nyc-MTA/tests
python3 -m unittest discover -s washdc-WMATA/tests
python3 -m unittest discover -s sf-BART/tests
```

The decoder's output is checked byte for byte against Google's reference protobuf library (snapshots in `common/tests/fixtures`, regenerated with `common/tools/make_snapshots.py`). `common/tools/profile_decoder.py` times the decoder on the fixtures under CPython or the MicroPython unix port and `--floor` reports the smallest heap it needs; `common/tools/profile_on_board.py` does the same on the MatrixPortal over the serial console, including download times. Set `PROFILE = True` in `nyc-MTA/code.py` or `washdc-WMATA/code.py` to log the timing of every fetch. See [common/README.md](common/README.md) for numbers.

## License

This project is licensed under the [GNU v3](LICENSE).
