# Arrivals Board for NYC Subway, DC Metro and BART

These files power a 64x32 RGB matrix display that shows arrival times for the New York City Subway, the Washington DC Metro Rail, or BART in the San Francisco Bay Area. I am currently using an Adafruit Matrixportal S3 microcontroller. It was vaguely inspired by Tidbyt products, but mostly just the form factor. You can [find instructions](#setup) on how to set this up yourself at the bottom.

<img src="/example.jpg" alt="example">

## Overview

New York City has the most extensive public transportation system in the United States, but due to its age (over 100 years old!) it is frequently in need of major maintenance which disrupts or delays service. To avoid needlessly waiting for trains on the platform, this display shows the next two trains traveling in one direction (the way I'm usually going) from the station closest to my apartment. Pushing the built-in `Up` button on the microcontroller displays the next `four` trains going in both directions.

The default screen also shows the time, temperature and AQI level. The AQI icon is color coded to signal the recommendations put out by the [US government AQI scale](https://www.airnow.gov/aqi/aqi-basics/). The subway line icons (known as 'bullets' in official parlance), will flash an alert symbol if the transit agency has issued an alert for that line. Pushing the onboard `Down` button will scroll the alerts along the bottom of the display.

Originally, I used an Adafruit Matrixportal M4, but it doesn't have enough memory for all the information and would frequently crash. I also would like to add additional functionality, so the additional memory is necessary.
<p align="center">
<img src="/arrivals_board.gif" alt="example2">
</p>

## Note on data

One program, [common/arrivals_board.py](common/arrivals_board.py), drives the display for every city; each city adds a small `city.py` with its sprites, direction names and a provider that fetches its agency's data. The NYC Subway and Washington DC Metro publish their real-time data as GTFS-Realtime protocol buffers. Google's protobuf library does not fit on a microcontroller, so the board uses a small streaming decoder of its own, [common/gtfsrt.py](common/gtfsrt.py), that reads the format directly and keeps only the trips and stops it needs. The decoder's working set is a few kilobytes: WMATA's feed streams through it, and the MTA feeds are downloaded gzipped (about 30 KB) and inflated in RAM (about 140 KB) first because that is 4 to 5 times less to transfer. The MTA feeds need no key but WMATA needs a free developer key. BART publishes a small JSON feed and is handled by [sf-BART](sf-BART/README.md). Stations and lines are set in `secrets.py`.

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

1. Follow the [instructions on this page](https://learn.adafruit.com/adafruit-matrixportal-s3/prep-the-matrixportal) to prepare the display and install CircuitPython (10 or newer: the certificate bundle in 9.x lacks the root that `api.wmata.com` chains to). Download the [library bundle](https://circuitpython.org/libraries) matching that CircuitPython version and place the following inside the `lib` folder on the board:
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

2. Accounts. The clock is set through Adafruit IO, so create a free account at https://io.adafruit.com and note your username and Active Key. Temperature needs a free [OpenWeather](https://openweathermap.org/api) key and AQI a free [IQAir](https://www.iqair.com/air-quality-monitors/api) key; leave either blank and the display shows `--` for that value. DC also needs a [WMATA developer key](https://developer.wmata.com). NYC needs no transit key. BART ships with BART's public key (see [sf-BART/README.md](sf-BART/README.md)).
3. Fill out `secrets_template.py` for your city according to the inline instructions and save it as `secrets.py`. NYC needs the GTFS stop ids of your station with their `N`/`S` suffix (from `stops.txt` in the [MTA GTFS zip](https://rrgtfsfeeds.s3.amazonaws.com/gtfs_subway.zip)) and the lines to show; DC needs station codes from the WMATA developer portal; BART needs the four-letter station abbreviation.
4. Build the drive folder for your city and copy its contents to the root of CIRCUITPY, together with `secrets.py`:

```bash
python3 pack.py nyc-MTA
```

   (`washdc-WMATA` or `sf-BART` likewise). The folder holds `code.py`, `city.py`, the city's data module, the shared `arrivals_board.py` and `feeds.py` from `common/` (plus `gtfsrt.py` for NYC and DC and `gtsr4.pem` for BART), the `img` folder and the three fonts. Copying those by hand works too.
5. It is best practice to use a serial monitor (e.g. the CircuitPython extension for VS Code) to ensure the code is running correctly before attaching the LED Matrix display as computer supplied USB-C power is often not enough to power the board and display. This can make it appear that the code is failing when the issue may actually be insufficient power. Any mistake in `secrets.py` (a misspelled line, a station id without its suffix, an unknown direction) stops the program at startup with a message naming the field.
6. Enjoy not waiting on the platform.

## Features

If you used a Matrixportal S3, it has three buttons built into the board. From top to bottom they are: `RESET`, `UP` and `DOWN`. Here is the current functionality of each button:

- `RESET` will reset the device and will reload the code, it's useful in case the board loses its wi-fi connection or other errors.
- `UP` will change the display to show the next four trains in both directions, as seen in the example gif above.
- `DOWN` scrolls any active alerts on the lines selected during setup, one alert at a time. Fetches run in the gaps between alerts so the text never stalls, the first train's time is refreshed in those gaps, and `UP` still works while it scrolls.

A city can also turn every text label red between two hours (`NIGHT_HOURS` in its `city.py`; BART uses 20:00 to 06:00) and show custom bullets until the first fetch (`STARTUP_TILES`). Set `profile=True` in `code.py` to print the timing of every transit fetch on the serial console.

## License

This project is licensed under the [GNU v3](LICENSE).
