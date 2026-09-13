"""Shared display program for the arrivals board (copy to the board next to code.py).

A city module supplies sprites, direction names and a Provider; this module builds
the display and runs the main loop without knowing which city it shows:

    import arrivals_board
    import city
    arrivals_board.run(city)

City module contract
--------------------
NAME             short agency name for console messages ("MTA")
SHEET            sprite sheet of 8x8 line bullets, two tiles per row
BULLETS          {line id: tile index}
FALLBACK_TILE    tile for unknown lines, no service and errors
ALERT_TILE       tile flashed while a line has an alert
BLANK_TILE       an all-black tile
ARROWS           (up bitmap path, down bitmap path, tile height) for the four-train screen
LABEL_X          (x of the up column, x of the down column) on the four-train screen
DIRECTIONS       (up key, down key) of the arrivals dictionary, e.g. ("North", "South")
DUE_TEXT         text for a train arriving now ("Due", "ARR")
REFRESH          seconds between arrivals fetches
ALERT_REFRESH    seconds between alert refreshes, 0 when the provider has none
NIGHT_HOURS      None, or (start_hour, end_hour): every text label is red between them
STARTUP_TILES    None, or (top tile, bottom tile) shown until the first fetch
Provider(secrets, network, profile)
    .default_direction  one of DIRECTIONS
    .fetch()            arrivals dictionary, or raises (feeds.FeedError for bad data)
    .refresh_alerts()   optional; fetches alerts into provider state in its own loop slot
    .reset()            close sockets after a failure

Arrivals dictionary: {DIRECTIONS[0]: [train, ...], DIRECTIONS[1]: [train, ...], "alerts": [text, ...]}
train: {"Line": str, "Arrival": int minutes (0 = due), "Alert": bool}
"""
import gc
import time

import board
import displayio
import keypad
import supervisor
import vectorio
import wifi
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.bitmap_label import Label as Bitmap_Label
from adafruit_display_text.label import Label
from adafruit_matrixportal.matrix import Matrix
from adafruit_matrixportal.network import Network
import adafruit_imageload as imageload

import feeds

LOOP_SLEEP = 0.5          # seconds between display updates when idle
SCROLL_PIXELS = 25        # alert text moves this many pixels per loop iteration...
SCROLL_STEP = 0.02        # ...one pixel every this many seconds
ARROW_PIXELS = 1          # arrow animation on the four-train screen: 1 px every 50 ms, as before
ARROW_STEP = 0.05
DEFAULT_ROWS = 2          # trains on the main screen
BOARD_ROWS = 4            # trains per direction on the four-train screen
BOARD_LINE_SPACING = 0.55  # helv-9's 15 px font box x 0.55 = 8 px rows: four rows fit 32 px, aligned with the bullets
MAX_FAILS = 5             # consecutive network failures before a reload
RELOAD_DELAY = 120        # seconds to wait before supervisor.reload()
CLOCK_SYNC_MS = 3600000
WEATHER_MS = 600000
AQI_MS = 900000
RETURN_MS = 1200000       # the four-train screen returns to the main screen after this
FLASH_ON_MS = 1000
FLASH_OFF_MS = 8000
ALERT_SLOT_GAP_MS = 5000  # alerts refresh only this long after a trip fetch, never in the same iteration
CLOCK_SYNCED_YEAR = 2024  # the RTC starts at 2000; a later year means the time service worked

BLACK = 0
RED = 1
AMBER = 2
GREEN = 3
WHITE = 4
NO_SERVICE_BOARD = "No\nSer\nvice\n"


def load_secrets():
    """The secrets.py dictionary; one place to change if settings move to settings.toml."""
    try:
        from secrets import secrets
    except ImportError:
        print("WiFi secrets are kept in secrets.py, please add them there!")
        raise
    return secrets


def set_color(label, value):
    """Write a label color only when it changes: the setter forces a full redraw."""
    if label.color != value:
        label.color = value


def set_tile(grid, row, index):
    """Write a tile index only when it changes: the setter marks the tile dirty regardless."""
    if grid[0, row] != index:
        grid[0, row] = index


class UI:
    """Every displayio object the board draws, built once from the city's assets."""

    def __init__(self, city):
        displayio.release_displays()
        self.keys = keypad.Keys((board.BUTTON_UP, board.BUTTON_DOWN), value_when_pressed=False, pull=True)
        matrix = Matrix()
        self.display = matrix.display
        self.network = Network(status_neopixel=board.NEOPIXEL, debug=False)
        width = self.display.width
        height = self.display.height
        y_center = height // 2
        ceiling = y_center - 2

        root = displayio.Group()
        background = displayio.Bitmap(width, height, 4)
        self.palette = displayio.Palette(7)
        self.palette[BLACK] = 0x000000
        self.palette[RED] = 0xFF0000
        self.palette[AMBER] = 0xCC4000
        self.palette[GREEN] = 0x00FF00
        self.palette[WHITE] = 0x808183
        root.append(displayio.TileGrid(background, pixel_shader=self.palette))
        self.display.root_group = root

        mins_icon = displayio.OnDiskBitmap("/img/mins_icon.bmp")
        mins_tile = displayio.TileGrid(mins_icon, pixel_shader=mins_icon.pixel_shader)
        mins_tile.x = width - 5
        mins_tile.y = 0

        aqi_sheet, aqi_palette = imageload.load("/img/aqi_sheet.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette)
        self.aqi_icon = displayio.TileGrid(aqi_sheet, pixel_shader=aqi_palette, width=1, height=1,
                                           tile_width=13, tile_height=5, default_tile=0)
        self.aqi_icon.x = 3
        self.aqi_icon.y = y_center - 4

        sheet, sheet_palette = imageload.load(city.SHEET, bitmap=displayio.Bitmap, palette=displayio.Palette)
        self.bullets = displayio.TileGrid(sheet, pixel_shader=sheet_palette, width=1, height=DEFAULT_ROWS,
                                          tile_width=8, tile_height=8, default_tile=city.FALLBACK_TILE)
        self.bullets.x = 24
        self.bullets.y = y_center - 1
        self.up_bullets = displayio.TileGrid(sheet, pixel_shader=sheet_palette, width=1, height=BOARD_ROWS,
                                             tile_width=8, tile_height=8, default_tile=city.FALLBACK_TILE)
        self.up_bullets.x = 5
        self.up_bullets.y = 0
        self.down_bullets = displayio.TileGrid(sheet, pixel_shader=sheet_palette, width=1, height=BOARD_ROWS,
                                               tile_width=8, tile_height=8, default_tile=city.FALLBACK_TILE)
        self.down_bullets.x = 31
        self.down_bullets.y = 0

        up_path, down_path, self.arrow_height = city.ARROWS
        up_bitmap, up_palette = imageload.load(up_path, bitmap=displayio.Bitmap, palette=displayio.Palette)
        down_bitmap, down_palette = imageload.load(down_path, bitmap=displayio.Bitmap, palette=displayio.Palette)
        self.up_arrow = displayio.TileGrid(up_bitmap, pixel_shader=up_palette, width=1, height=1,
                                           tile_width=5, tile_height=self.arrow_height)
        self.up_arrow.x = 25
        self.up_arrow.y = height
        self.down_arrow = displayio.TileGrid(down_bitmap, pixel_shader=down_palette, width=1, height=1,
                                             tile_width=5, tile_height=self.arrow_height)
        self.down_arrow.x = width - 12
        self.down_arrow.y = -self.arrow_height

        self.up_rectangle = vectorio.Rectangle(pixel_shader=self.palette, width=5, height=7, x=25, y=0, color_index=BLACK)
        self.up_rectangle.hidden = True
        self.down_rectangle = vectorio.Rectangle(pixel_shader=self.palette, width=5, height=7, x=width - 12, y=0, color_index=BLACK)
        self.down_rectangle.hidden = True

        large_font = bitmap_font.load_font("fonts/helvR14.bdf")
        small_font = bitmap_font.load_font("fonts/helvR10.bdf")
        board_font = bitmap_font.load_font("fonts/helv-9.bdf")

        self.clock_label = Label(large_font, anchor_point=(0.5, 0.5), anchored_position=(44, 7))
        self.weather_label = Label(small_font)
        self.weather_label.x = 4
        self.weather_label.y = y_center + 6
        self.aqi_label = Label(small_font)
        self.aqi_label.x = 4
        self.aqi_label.y = 6
        self.arrival_label_1 = Label(small_font, color=self.palette[WHITE], anchor_point=(1.0, 0.0), anchored_position=(width, ceiling))
        self.arrival_label_2 = Label(small_font, color=self.palette[WHITE], anchor_point=(1.0, 0.0), anchored_position=(width, ceiling + 9))
        self.alert_label = Bitmap_Label(small_font)
        self.alert_label.x = width
        self.alert_label.y = 26
        self.alert_label.color = self.palette[WHITE]

        self.row_numbers = Bitmap_Label(font=board_font, text="1\n2\n3\n4", color=self.palette[WHITE], line_spacing=BOARD_LINE_SPACING,
                                        anchor_point=(0.0, 0.0), anchored_position=(0, 0), background_tight=True)
        self.up_label = Label(font=board_font, text="", color=self.palette[WHITE], line_spacing=BOARD_LINE_SPACING,
                              anchor_point=(0.0, 0.0), anchored_position=(city.LABEL_X[0], 0), background_tight=True)
        self.down_label = Label(font=board_font, text="", color=self.palette[WHITE], line_spacing=BOARD_LINE_SPACING,
                                anchor_point=(0.0, 0.0), anchored_position=(city.LABEL_X[1], 0), background_tight=True)

        self.default_group = displayio.Group()
        for element in (self.clock_label, self.bullets, self.aqi_icon, self.weather_label, self.aqi_label,
                        self.arrival_label_1, self.arrival_label_2, self.alert_label):
            self.default_group.append(element)
        self.arrivals_group = displayio.Group()
        for element in (self.row_numbers, self.up_bullets, self.down_bullets, self.up_arrow, self.down_arrow,
                        self.up_rectangle, self.down_rectangle, self.up_label, self.down_label, mins_tile):
            self.arrivals_group.append(element)
        root.append(self.default_group)
        root.append(self.arrivals_group)
        self.default_group.hidden = False
        self.arrivals_group.hidden = True

    def color(self, index):
        return self.palette[index]

    def change_screen(self):
        self.default_group.hidden = not self.default_group.hidden
        self.arrivals_group.hidden = not self.arrivals_group.hidden

    def pause(self, seconds):
        """Sleep in 50 ms slices, returning early when a button event arrives."""
        end = feeds.now_ms() + int(seconds * 1000)
        while feeds.now_ms() < end:
            if len(self.keys.events):
                return
            time.sleep(0.05)


class Atmosphere:
    """Temperature from OpenWeatherMap and AQI from IQAir; both optional."""

    def __init__(self, secrets, ui, debug=False):
        self.ui = ui
        self.debug = debug
        self.temperature = None  # None until the first successful fetch: the display shows "--"
        self.aqi = None
        latitude = secrets["latitude"]
        longitude = secrets["longitude"]
        self.weather_url = "https://api.openweathermap.org/data/2.5/weather?lat={}&lon={}&appid={}&units=imperial".format(
            latitude, longitude, secrets["openweather_key"])
        self.aqi_url = "https://api.airvisual.com/v2/nearest_city?lat={}&lon={}&key={}".format(
            latitude, longitude, secrets["iqair_key"])

    def weather_api(self):
        try:
            weather = self.ui.network.fetch_data(self.weather_url, json_path=[])
            if self.debug:
                print("Weather:", weather)
            self.temperature = round(weather["main"]["temp"])
        except Exception as e:
            print("Weather api call error:", e)

    def aqi_api(self):
        try:
            pollution = self.ui.network.fetch_data(self.aqi_url, json_path=["data", "current", "pollution"])
            if self.debug:
                print("AQI:", pollution)
            value = pollution.get("aqius")
            if not isinstance(value, int):
                print("AQI: unexpected aqius value", value)
                return
            self.aqi = value
        except Exception as e:
            print("AQI api call error:", e)  # IQAir answers 403 "Forbidden" for a bad or missing key

    def update_display(self, text_color):
        ui = self.ui
        set_color(ui.weather_label, text_color)
        set_color(ui.aqi_label, text_color)
        ui.weather_label.text = "--°" if self.temperature is None else "{}°".format(self.temperature)
        if self.aqi is None:
            ui.aqi_label.text = "--"
            set_tile(ui.aqi_icon, 0, 0)
            return
        ui.aqi_label.text = " {}".format(self.aqi) if self.aqi < 10 else str(self.aqi)
        levels = (50, 100, 150, 200, 300)
        tile = 1
        for limit in levels:
            if self.aqi > limit:
                tile += 1
        set_tile(ui.aqi_icon, 0, tile)


class Board:
    """Draws arrivals on the two screens; all city-specific values come from ``city``."""

    def __init__(self, city, ui, provider, debug=False):
        self.city = city
        self.ui = ui
        self.provider = provider
        self.debug = debug
        self.up, self.down = city.DIRECTIONS
        self.default_direction = provider.default_direction
        self.night_hours = getattr(city, "NIGHT_HOURS", None)
        self.last_error = None
        self.prev_time = -1
        self.alert_flash = False
        self.queue = [{"Line": None, "Arrival": 0, "ALERT": False, "FLASH": False, "PREV_TIME": -1} for _ in range(DEFAULT_ROWS)]
        startup = getattr(city, "STARTUP_TILES", None)
        if startup:
            for row, tile in enumerate(startup[:DEFAULT_ROWS]):
                set_tile(ui.bullets, row, tile)

    # ------------------------------------------------------------------ helpers
    def bullet(self, line):
        return self.city.BULLETS.get(line, self.city.FALLBACK_TILE)

    def is_night(self):
        if not self.night_hours:
            return False
        now = time.localtime()
        if now[0] < CLOCK_SYNCED_YEAR:
            return False  # the clock has not been set yet
        start, end = self.night_hours
        return now[3] >= start or now[3] < end

    def text_color(self, day_index=WHITE):
        return self.ui.color(RED) if self.is_night() else self.ui.color(day_index)

    def fetch_arrivals(self):
        """The provider's arrivals or None; remembers why it failed for the reload logic."""
        self.last_error = None
        try:
            data = self.provider.fetch()
            if self.debug:
                print(self.city.NAME, "arrivals:", data)
            return data
        except Exception as e:
            self.last_error = e
            print(self.city.NAME, "arrivals error:", e)
            if not isinstance(e, feeds.FeedError):
                self.provider.reset()
            return None
        finally:
            gc.collect()

    def update_time(self):
        now = time.localtime()
        set_color(self.ui.clock_label, self.text_color(GREEN))
        self.ui.clock_label.text = "{:02d}:{:02d}".format(now[3], now[4])

    def wifi_lost(self):
        ui = self.ui
        if ui.default_group.hidden:
            ui.change_screen()
        set_color(ui.arrival_label_1, ui.color(RED))
        set_color(ui.arrival_label_2, ui.color(RED))
        ui.arrival_label_1.text = "WiFi "
        ui.arrival_label_2.text = "LOST"
        for row in range(DEFAULT_ROWS):
            set_tile(ui.bullets, row, self.city.FALLBACK_TILE)

    # ------------------------------------------------------------ main screen
    def update_display(self, arrival_data, bullet_alert_flag, now, only_first=False):
        """Draw the main screen's train rows. ``only_first`` leaves row 2 alone: it is
        blank while the alert text scrolls, but the first train's time still matters."""
        ui = self.ui
        city = self.city
        text = self.text_color()
        limit = 1 if only_first else DEFAULT_ROWS
        set_color(ui.arrival_label_1, text)
        if not only_first:
            set_color(ui.arrival_label_2, text)

        if arrival_data is None:
            ui.arrival_label_1.text = "Error"
            if not only_first:
                ui.arrival_label_2.text = "Error"
            for row in range(limit):
                set_tile(ui.bullets, row, city.FALLBACK_TILE)
            return

        trains = arrival_data[self.default_direction]
        if not trains:
            for row in range(limit):
                set_tile(ui.bullets, row, city.FALLBACK_TILE)
            ui.arrival_label_1.text = "No"
            if not only_first:
                ui.arrival_label_2.text = "Service"
            return

        rows = min(DEFAULT_ROWS, len(trains))
        for i in range(rows):
            train = trains[i]
            entry = self.queue[i]
            entry["Line"] = train["Line"]
            entry["Arrival"] = train["Arrival"]
            entry["FLASH"] = self.alert_flash
            entry["PREV_TIME"] = self.prev_time
            entry["ALERT"] = bool(train.get("Alert", False))

        for row in range(min(rows, limit)):
            entry = self.queue[row]
            minutes = entry["Arrival"]
            label = ui.arrival_label_1 if row == 0 else ui.arrival_label_2
            label.text = city.DUE_TEXT if minutes == 0 else "{}min".format(minutes)
            if self.debug:
                print("Row {} -> {} {} min alert={}".format(row + 1, entry["Line"], minutes, entry["ALERT"]))

            if entry["ALERT"] and bullet_alert_flag:
                if entry["FLASH"]:
                    if now >= entry["PREV_TIME"] + FLASH_OFF_MS:
                        self.prev_time = now
                        set_tile(ui.bullets, row, city.ALERT_TILE)
                        self.alert_flash = False
                elif now >= entry["PREV_TIME"] + FLASH_ON_MS:
                    self.prev_time = now
                    set_tile(ui.bullets, row, self.bullet(entry["Line"]))
                    self.alert_flash = True
            else:
                set_tile(ui.bullets, row, self.bullet(entry["Line"]))

        if rows == 1 and not only_first:
            set_tile(ui.bullets, 1, city.BLANK_TILE)
            ui.arrival_label_2.text = ""

    def display_alt_text(self):
        """Make room for the scrolling alert text."""
        self.ui.arrival_label_2.text = ""
        self.ui.weather_label.text = ""
        set_tile(self.ui.bullets, 1, self.city.BLANK_TILE)

    def alert_keys(self, arrival_data):
        """What the DOWN button acknowledges: every alert text, plus every line that is
        flagged without one (BART's late trains). Trains rotating through the two rows
        do not change the keys, so an acknowledged alert stays quiet while it lasts."""
        keys = set(arrival_data["alerts"])
        for train in arrival_data[self.default_direction]:
            if train.get("Alert", False):
                keys.add("line:" + str(train["Line"]))
        return keys

    def alert_items(self, arrival_data):
        """One string per alert, scrolled one after another by the DOWN button."""
        if arrival_data is None or not arrival_data["alerts"]:
            return ["No active alerts."]
        return ["{}.{}".format(i + 1, text) for i, text in enumerate(arrival_data["alerts"])]

    # ------------------------------------------------------- four-train screen
    def update_board(self, arrival_data):
        ui = self.ui
        city = self.city
        board_color = self.text_color()
        set_color(ui.row_numbers, board_color)
        set_color(ui.up_label, board_color)
        set_color(ui.down_label, board_color)

        if arrival_data is None:
            ui.up_label.text = "err\nerr\nerr\nerr"
            ui.down_label.text = "err\nerr\nerr\nerr"
            for i in range(BOARD_ROWS):
                set_tile(ui.up_bullets, i, city.FALLBACK_TILE)
                set_tile(ui.down_bullets, i, city.FALLBACK_TILE)
            ui.up_rectangle.hidden = True
            ui.down_rectangle.hidden = True
            return

        for direction, bullets, label, rectangle in (
                (self.up, ui.up_bullets, ui.up_label, ui.up_rectangle),
                (self.down, ui.down_bullets, ui.down_label, ui.down_rectangle)):
            trains = arrival_data[direction]
            rows = min(BOARD_ROWS, len(trains))
            if rows == 0:
                label.text = NO_SERVICE_BOARD
                for i in range(BOARD_ROWS):
                    set_tile(bullets, i, city.FALLBACK_TILE)
                rectangle.hidden = True
                continue
            lines = []
            for i in range(rows):
                train = trains[i]
                set_tile(bullets, i, self.bullet(train["Line"]))
                minutes = train["Arrival"]
                if minutes == 0:
                    lines.append(city.DUE_TEXT)
                elif minutes < 10:
                    lines.append(" {}".format(minutes))
                else:
                    lines.append(str(minutes))
            rectangle.hidden = trains[0]["Arrival"] != 0
            label.text = "\n".join(lines) + "\n"
            for i in range(rows, BOARD_ROWS):
                set_tile(bullets, i, city.BLANK_TILE)

    def scroll_arrows(self):
        """Run the arrows across the screen after a fetch on the four-train screen (about 3.5 s)."""
        ui = self.ui
        while ui.down_arrow.y < ui.display.height:
            ui.up_arrow.y -= ARROW_PIXELS
            ui.down_arrow.y += ARROW_PIXELS
            time.sleep(ARROW_STEP)
        ui.up_arrow.y = ui.display.height
        ui.down_arrow.y = -ui.arrow_height


class Runner:
    """The main loop as a stepper, so one iteration can be driven at a time."""

    def __init__(self, city, ui, provider, board_, atmosphere, secrets, debug=False):
        self.city = city
        self.ui = ui
        self.provider = provider
        self.board = board_
        self.atmosphere = atmosphere
        self.ssid = secrets["ssid"]
        self.password = secrets["password"]
        self.debug = debug
        self.refresh_ms = int(city.REFRESH * 1000)
        self.alert_refresh_ms = int(getattr(city, "ALERT_REFRESH", 0) * 1000)
        self.clock_check = None
        self.weather_check = None
        self.aqi_check = None
        self.arrivals_check = None
        self.alert_check = None
        self.return_to_default = None
        self.arrival_data = None
        self.api_fails = 0
        self.bullet_alert_flag = True
        self.alert_items = []
        self.alert_keys = set()     # what is currently alert-worthy (see Board.alert_keys)
        self.acknowledged = set()   # the keys the DOWN button has been pressed for
        self.alert_queue = []       # alerts still to scroll after the DOWN button
        self.alert_moving = False   # one alert is on its way across the screen

    @property
    def scrolling(self):
        """True from the DOWN press until the last alert has left the screen."""
        return self.alert_moving or bool(self.alert_queue)

    def due(self, last, interval_ms, now):
        return last is None or now - last > interval_ms

    def stop_scrolling(self):
        if self.scrolling:
            self.alert_queue = []
            self.alert_moving = False
            self.ui.alert_label.x = self.ui.display.width

    def step(self):
        ui = self.ui
        if not feeds.ensure_wifi(self.ssid, self.password, on_reconnect=self.provider.reset):
            self.stop_scrolling()  # the LOST message needs the alert row
            self.board.wifi_lost()
            self.atmosphere.update_display(self.board.text_color())  # the scroll may have blanked the weather
            time.sleep(5)  # nothing here handles a press, so no early return
            ui.keys.events.clear()  # presses made during the outage do not replay after reconnect
            return
        now = feeds.now_ms()
        if not self.alert_moving:  # a fetch would freeze moving text: it waits for the gap between alerts
            self.run_fetches(now)
            now = feeds.now_ms()  # the fetches block for seconds; the timers below need the current time
        event = ui.keys.events.get()
        if event and event.pressed:
            if event.key_number == 1:  # DOWN: scroll the alerts one after another
                self.board.display_alt_text()
                self.bullet_alert_flag = False
                self.acknowledged = set(self.alert_keys)
                self.alert_queue = list(self.alert_items)
                self.alert_moving = False
            elif event.key_number == 0:  # UP: switch screens
                self.stop_scrolling()  # the alert row is not part of the other screen
                ui.change_screen()
                if ui.default_group.hidden:
                    self.return_to_default = now

        if not ui.arrivals_group.hidden:
            self.board.update_board(self.arrival_data)
            if self.return_to_default is not None and now - self.return_to_default > RETURN_MS:
                ui.change_screen()

        if not ui.default_group.hidden:
            if not self.scrolling:
                self.board.update_display(self.arrival_data, self.bullet_alert_flag, now)
                self.board.update_time()
                self.atmosphere.update_display(self.board.text_color())
            elif not self.alert_moving:  # the gap between alerts: refresh the first train only
                self.board.update_display(self.arrival_data, self.bullet_alert_flag, now, only_first=True)

        if self.scrolling:
            if not self.alert_moving:  # start the next alert from the right edge
                ui.alert_label.text = self.alert_queue.pop(0)
                ui.alert_label.x = ui.display.width
                self.alert_moving = True
            set_color(ui.alert_label, self.board.text_color())
            for _ in range(SCROLL_PIXELS):
                if self.scroll_alert():
                    self.alert_moving = False  # the next step fetches if due, then starts the next alert
                    ui.keys.events.clear()     # presses made during the scroll do not replay
                    break
                time.sleep(SCROLL_STEP)
        else:
            ui.pause(LOOP_SLEEP)

    def run_fetches(self, now):
        """Every timed network call: clock sync, weather, AQI, arrivals, alerts."""
        ui = self.ui
        if self.due(self.clock_check, CLOCK_SYNC_MS, now):
            try:
                self.board.update_time()
                ui.network.get_local_time()
            except Exception as e:  # WiFi or HTTP failures raise OSError, not just RuntimeError
                print("CLOCK UPDATE ERROR:", e)
            self.clock_check = now

        if self.due(self.weather_check, WEATHER_MS, now):
            self.atmosphere.weather_api()
            self.weather_check = now

        if self.due(self.aqi_check, AQI_MS, now):
            self.atmosphere.aqi_api()
            self.aqi_check = now

        if self.due(self.arrivals_check, self.refresh_ms, now):
            gc.collect()
            self.arrival_data = self.board.fetch_arrivals()
            if self.arrival_data is not None:
                self.api_fails = 0
            elif not isinstance(self.board.last_error, feeds.FeedError):
                self.api_fails += 1  # only network-level failures count toward the reload
            if self.api_fails > MAX_FAILS:
                print("Repeated network failures, reloading in", RELOAD_DELAY, "s")
                ui.clock_label.text = "reset"
                time.sleep(RELOAD_DELAY)
                supervisor.reload()
            self.alert_items = self.board.alert_items(self.arrival_data)
            if self.arrival_data is not None:  # a failed fetch changes nothing
                self.alert_keys = self.board.alert_keys(self.arrival_data)
                self.acknowledged &= self.alert_keys  # an acknowledgement lasts as long as its alert does
                self.bullet_alert_flag = not self.alert_keys <= self.acknowledged  # anything unseen flashes
            if not ui.arrivals_group.hidden:
                self.board.update_board(self.arrival_data)
                self.board.scroll_arrows()
            self.arrivals_check = feeds.now_ms()
        elif (self.alert_refresh_ms and hasattr(self.provider, "refresh_alerts")
              and self.due(self.alert_check, self.alert_refresh_ms, now)
              and self.arrivals_check is not None and now - self.arrivals_check > ALERT_SLOT_GAP_MS):
            self.provider.refresh_alerts()  # its own iteration, so the two freezes never stack
            self.alert_check = feeds.now_ms()


    def scroll_alert(self):
        """Move the alert text one pixel left; True once it has fully left the screen."""
        label = self.ui.alert_label
        label.x -= 1
        if label.x < -label.bounding_box[2]:
            label.x = self.ui.display.width
            return True
        return False


def run(city, debug=False, profile=False):
    secrets = load_secrets()
    print("Time will be set for {}".format(secrets["timezone"]))
    ui = UI(city)
    feeds.disable_wifi_sleep()
    provider = city.Provider(secrets, ui.network, profile)
    board_ = Board(city, ui, provider, debug)
    atmosphere = Atmosphere(secrets, ui, debug)
    board_.update_time()
    try:
        ui.network.connect()  # PortalBase's first connect; later drops are handled by feeds.ensure_wifi
    except Exception as e:
        print("WiFi connect failed:", e)
    runner = Runner(city, ui, provider, board_, atmosphere, secrets, debug)
    while True:
        runner.step()
