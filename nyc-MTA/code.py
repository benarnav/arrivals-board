import time
import board
import keypad
import displayio
import terminalio
import vectorio
from adafruit_display_text.label import Label
from adafruit_display_text.bitmap_label import Label as Bitmap_Label
from adafruit_bitmap_font import bitmap_font
from adafruit_matrixportal.network import Network
from adafruit_matrixportal.matrix import Matrix
import adafruit_imageload as imageload
import supervisor
import gc
import wifi

DEBUG = False
bullet_index = {"A" : 0,
                "C" : 1,
                "E" : 2,
                "B" : 3,
                "D" : 4,
                "F" : 5,
                "M" : 6,
                "G" : 7,
                "J" : 8,
                "Z" : 9,
                "L" : 10,
                "N" : 11,
                "Q" : 12,
                "R" : 13,
                "W" : 14,
                "S" : 15,
                "1" : 16,
                "2" : 17,
                "3" : 18,
                "4" : 19,
                "5" : 20,
                "6" : 21,
                "7" : 22,
                "7E": 23,
                "6E": 24,
                "SIR":25,
                "ALERT":26,
                "MTA":27,
                "FE":28,
                "BLANK":37}

# release any currently configured displays
displayio.release_displays()

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise
print("Time will be set for {}".format(secrets["timezone"]))

keys = keypad.Keys((board.BUTTON_UP,board.BUTTON_DOWN), value_when_pressed=False, pull=True)

# --- Display setup ---
matrix = Matrix()
display = matrix.display
network = Network(status_neopixel=board.NEOPIXEL, debug=False)

# --- Drawing setup ---
root_group = displayio.Group()  # Create a Group
bitmap = displayio.Bitmap(64, 32, 4)  # Create a bitmap object, width, height, bit depth
color = displayio.Palette(7)  # Create a color palette
color[0] = 0x000000  # black background
color[1] = 0xFF0000  # red
color[2] = 0xCC4000  # amber
color[3] = 0x00ff00  # greenish
color[4] = 0x808183  # white

# Create a TileGrid using the Bitmap and Palette
y_center = display.height // 2
cieling = y_center - 2

tile_grid = displayio.TileGrid(bitmap, pixel_shader=color,)
root_group.append(tile_grid)  # ELEMENT 0, Add the TileGrid to the Group
display.root_group = root_group

mins_icon = displayio.OnDiskBitmap("/img/mins_icon.bmp")
mins_tile = displayio.TileGrid(mins_icon, pixel_shader=mins_icon.pixel_shader)
mins_tile.x = display.width - 5
mins_tile.y = 0

aqi_sheet, aqi_palette = imageload.load("/img/aqi_sheet.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette)
aqi_lvl = displayio.TileGrid(aqi_sheet,
                               pixel_shader=aqi_palette,
                               width=1,
                               height=1,
                               tile_width=13,
                               tile_height=5,
                               default_tile=0)
aqi_lvl.x = 3
aqi_lvl.y = y_center - 4

mta_sheet, mta_palette = imageload.load("/img/mta_sheet.bmp",
                            bitmap=displayio.Bitmap,
                            palette=displayio.Palette)
mta_bullets = displayio.TileGrid(mta_sheet,
                               pixel_shader=mta_palette,
                               width=1,
                               height=2,
                               tile_width=8,
                               tile_height=8,
                               default_tile=27)
mta_bullets.x = 24
mta_bullets.y = y_center - 1

arrivals_north_bullets = displayio.TileGrid(mta_sheet,
                               pixel_shader=mta_palette,
                               width=1,
                               height=4,
                               tile_width=8,
                               tile_height=8,
                               default_tile=27)
arrivals_north_bullets.x = 5
arrivals_north_bullets.y = 0

arrivals_south_bullets = displayio.TileGrid(mta_sheet,
                               pixel_shader=mta_palette,
                               width=1,
                               height=4,
                               tile_width=8,
                               tile_height=8,
                               default_tile=27)
arrivals_south_bullets.x = 31
arrivals_south_bullets.y = 0

arrivals_arrow_north, arrow_n_palette = imageload.load("/img/train_NORTH.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette)
arrivals_arrow_south, arrow_s_palette = imageload.load("/img/train_SOUTH.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette)
arrivals_north_arrow = displayio.TileGrid(arrivals_arrow_north,
                                          pixel_shader=arrow_n_palette,
                                          width=1,
                                          height=1,
                                          tile_width=5,
                                          tile_height=39)
arrivals_north_arrow.x = 25
arrivals_north_arrow.y = display.height

arrivals_south_arrow = displayio.TileGrid(arrivals_arrow_south,
                                          pixel_shader=arrow_s_palette,
                                          width=1,
                                          height=1,
                                          tile_width=5,
                                          tile_height=39)
arrivals_south_arrow.x = display.width - 12
arrivals_south_arrow.y =  -39

north_rectangle = vectorio.Rectangle(pixel_shader=color,
                                     width=5,
                                     height=7,
                                     x=25,
                                     y=0,
                                     color_index=0)
north_rectangle.hidden = True

south_rectangle = vectorio.Rectangle(pixel_shader=color,
                                     width=5,
                                     height=7,
                                     x=display.width - 12,
                                     y=0,
                                     color_index=0)
south_rectangle.hidden = True

if not DEBUG:
    large_font = bitmap_font.load_font("fonts/helvR14.bdf") 
    small_font = bitmap_font.load_font("fonts/helvR10.bdf")
    arrival_board_font = bitmap_font.load_font("fonts/helv-9.bdf")
else:
    font = terminalio.FONT

clock_label = Label(large_font, anchor_point=(0.5,0.5), anchored_position=(44, 7))

weather_label = Label(small_font)
weather_label.x = 4
weather_label.y = y_center + 6

aqi_label = Label(small_font)
aqi_label.x = 4
aqi_label.y = 6

arrival_label_1 = Label(small_font, color=color[4], anchor_point=(1.0,0.0), anchored_position=(display.width, cieling))
arrival_label_2 = Label(small_font, color=color[4], anchor_point=(1.0,0.0), anchored_position=(display.width, cieling + 9))

alert_scroll_label = Bitmap_Label(small_font)
alert_scroll_label.x = display.width
alert_scroll_label.y = 26
alert_scroll_label.color = color[4]

arrivals_row_nums = Bitmap_Label(font=arrival_board_font,
                                 text="1\n2\n3\n4",
                                 color=color[4],
                                 line_spacing=0.6,
                                 anchor_point=(0.0,0.0),
                                 anchored_position=(0,0),
                                 background_tight=True)

arrivals_north_label = Label(font=arrival_board_font,
                                 text="",
                                 color=color[4],
                                 line_spacing=0.6,
                                 anchor_point=(0.0,0.0),
                                 anchored_position=(15,0),
                                 background_tight=True)

arrivals_south_label = Label(font=arrival_board_font,
                                 text="",
                                 color=color[4],
                                 line_spacing=0.6,
                                 anchor_point=(0.0,0.0),
                                 anchored_position=(40,0),
                                 background_tight=True)

class Atmosphere:
    def __init__(self):
        self.atmos_data = {"current_temp" : 0,
                           "high_temp" : 0,
                           "low_temp" : 0,
                           "feels_temp" : 0,
                           "aqi" : 0}
        self.latitude = secrets["latitude"]
        self.longitude = secrets["longitude"]
        self.openweather_key = secrets["openweather_key"]
        self.aqi_key = secrets["iqair_key"]
        self.openweather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={self.latitude}&lon={self.longitude}&appid={self.openweather_key}&units=imperial"
        self.iqair_url = f"http://api.airvisual.com/v2/nearest_city?lat={self.latitude}&lon={self.longitude}&key={self.aqi_key}"

    def weather_api(self):
        try:
            weather = network.fetch_data(self.openweather_url, json_path=[])
            if DEBUG:
                print("\n=== Calling Weather API ===")
                print(f"URL: {self.openweather_url}")
                print("Weather Data Retrieved:")
                print(weather)
        except Exception as e:
            if DEBUG:
                print("Weather api call error: ", e)
            return None

        self.atmos_data["current_temp"] = round(weather['main']['temp'])
        self.atmos_data["high_temp"] = round(weather['main']['temp_max'])
        self.atmos_data["low_temp"] = round(weather['main']['temp_min'])
        self.atmos_data["feels_temp"] = round(weather['main']['feels_like'])

    def aqi_api(self):
        try:
            aqi = network.fetch_data(self.iqair_url, json_path=["data", "current", "pollution"])
            if DEBUG:
                print("\n=== Calling AQI API ===")
                print(f"URL: {self.iqair_url}")
                print("AQI Data Retrieved:")
                print(aqi)
        except Exception as e:
            if DEBUG:
                print("AQI api call error: ", e)
            return None

        self.atmos_data["aqi"] = aqi["aqius"]

    def update_display(self):
        if self.atmos_data is None:
            weather_label.text = "e" + "°"
            aqi_label.text = "e"
            aqi_lvl[0] = 0
            return

        weather_label.text = "{temp}°".format(temp=self.atmos_data["current_temp"])  #pick what value you want displayed from atmos_data

        if self.atmos_data["aqi"] < 10:
            aqi_label.text = " {aqi}".format(aqi=self.atmos_data["aqi"])
        else:
            aqi_label.text = str(self.atmos_data["aqi"])

        weather_label.color = color[4]
        aqi_label.color = color[4]

        aqi_num = self.atmos_data["aqi"]
        if aqi_num <= 50:
            aqi_lvl[0] = 1
        elif aqi_num > 50 and aqi_num <= 100:
            aqi_lvl[0] = 2
        elif aqi_num > 100 and aqi_num <= 150:
            aqi_lvl[0] = 3
        elif aqi_num > 150 and aqi_num <= 200:
            aqi_lvl[0] = 4
        elif aqi_num > 200 and aqi_num <= 300:
            aqi_lvl[0] = 5
        elif aqi_num > 300:
            aqi_lvl[0] = 6


class Arrivals:
    def __init__(self):
        self.url = secrets["transit_url"]
        self.headers = secrets["transit_headers"]  # {'api-key': api_key, 'user-station': "", (optional) 'user-station-ids': "", 'subway-lines': ""}
        self.arrow_refresh = None
        self.default_rows = 2
        self.prev_time = -1
        self.alert_flash = False
        self.directions = ["North", "South"]
        self.no_service_board = "No\nSer\nvice\n"
        self.default_direction = secrets['default_direction']
        self.arrivals_queue = [
                            {"Line" : None,
                             "Arrival" : 0,
                             "ALERT" : False,
                             "FLASH_ON" : 1,
                             "FLASH_OFF" : 8,
                             "FLASH" : False,
                             "PREV_TIME" : -1},
                             {"Line" : None,
                             "Arrival" : 0,
                             "ALERT" : False,
                             "FLASH_ON" : 1,
                             "FLASH_OFF" : 8,
                             "FLASH" : False,
                             "PREV_TIME" : -1}]
    def wifi_lost_message(self):
        if default_group.hidden:
            change_screen()
        arrival_label_1.color = color[1]
        arrival_label_2.color = color[1]
        arrival_label_1.text = "WiFi "
        arrival_label_2.text = "LOST" 
        
        for row in range(2):
            mta_bullets[0,row] = bullet_index["MTA"]

    def api_call(self):
        if DEBUG:
            print("\n=== Calling MTA Arrivals API ===")
            print(f"URL: {self.url}")
            print(f"Headers: {self.headers}")

        try:
            arrival_data = network.fetch_data(self.url, json_path=[], headers=self.headers)
            if DEBUG:
                print("API Call Successful!")
                print("Raw API Response:")
                print(arrival_data)

        except Exception as e:
            if DEBUG:
                print("Arrival API call error:", e)
            return None

        return arrival_data

    def update_board(self, arrival_data):
        if not wifi.radio.connected:
            self.wifi_lost_message()
            
            return
        
        if arrival_data is None:
            arrivals_north_label.text = "err\nerr\nerr\nerr"
            arrivals_south_label.text = "err\nerr\nerr\nerr"
            for i in range(4):
                arrivals_north_bullets[0,i] = bullet_index["MTA"]
                arrivals_south_bullets[0,i] = bullet_index["MTA"]

            return

        for direction in self.directions:
            rows = min(4, len(arrival_data[direction]))
            arrival_board_times = ""

            if rows == 0:
                arrivals_north_label.text = self.no_service_board
                arrivals_south_label.text = self.no_service_board
                for i in range(4):
                    if direction == "North":
                        arrivals_north_bullets[0,i] = bullet_index["MTA"]
                    else:
                        arrivals_south_bullets[0,i] = bullet_index["MTA"]

                continue

            for i in range(rows):
                if direction == "North":
                    arrivals_north_bullets[0,i] = bullet_index[arrival_data["North"][i]["Line"]]
                else:
                    arrivals_south_bullets[0,i] = bullet_index[arrival_data["South"][i]["Line"]]
                arrival_time = arrival_data[direction][i]["Arrival"]

                if arrival_data[direction][0]["Arrival"] != 0:
                    if direction == "North":
                        north_rectangle.hidden = True
                    else:
                        south_rectangle.hidden = True

                if arrival_time == 0:
                    arrival_time = "Due"
                    if direction == "North":
                        north_rectangle.hidden = False
                    else:
                        south_rectangle.hidden = False

                elif arrival_time < 10:
                    arrival_time = f" {arrival_data[direction][i]["Arrival"]}"

                else:
                    arrival_time = str(arrival_data[direction][i]["Arrival"])
                arrival_board_times += arrival_time + "\n"

            if direction == "North":
                arrivals_north_label.text = arrival_board_times
            else:
                arrivals_south_label.text = arrival_board_times

            if rows < 4:
                for n in range(rows, 4):
                    if direction == "North":
                        arrivals_north_bullets[0,n] = bullet_index["BLANK"]
                    else:
                        arrivals_south_bullets[0,n] = bullet_index["BLANK"]

    def scroll_board_directions(self):
        while arrivals_south_arrow.y < display.height:
            arrivals_north_arrow.y = arrivals_north_arrow.y - 1
            arrivals_south_arrow.y = arrivals_south_arrow.y + 1
            time.sleep(0.05)
        arrivals_north_arrow.y = display.height
        arrivals_south_arrow.y = -39

    def update_display(self, arrival_data, bullet_alert_flag, now):
        if not wifi.radio.connected:
            self.wifi_lost_message()
            return
        
        if arrival_data is None:
            arrival_label_1.text = "Error"
            arrival_label_2.text = "Error"
            for row in range(2):
                mta_bullets[0,row] = bullet_index["MTA"]
            return

        if not arrival_data[self.default_direction]:
            for row in range(2):
                mta_bullets[0,row] = bullet_index["MTA"]
            arrival_label_1.text = "No"
            arrival_label_2.text = "Service"
            return

        affected_lines = [alert[0] for alert in arrival_data["alerts"]]
        rows = min(self.default_rows, len(arrival_data[self.default_direction]))
        
        for i in range(rows):
            self.arrivals_queue[i]["Line"] = arrival_data[self.default_direction][i]["Line"]
            self.arrivals_queue[i]["Arrival"] = arrival_data[self.default_direction][i]["Arrival"]
            self.arrivals_queue[i]["FLASH"] = self.alert_flash
            self.arrivals_queue[i]["PREV_TIME"] = self.prev_time
            self.arrivals_queue[i]["ALERT"] = False
            if self.arrivals_queue[i]["Line"] in affected_lines:
                self.arrivals_queue[i]["ALERT"] = True

        for row, train in enumerate(self.arrivals_queue):
            arrival_time = train["Arrival"]
            if arrival_time == 0:
                arrival_time = "Due"
            else:
                arrival_time = f"{arrival_time}min"

            if row == 0:
                arrival_label_1.text = arrival_time

            elif row == 1:
                arrival_label_2.text = arrival_time

            if DEBUG:
                print(f"Row {row+1} → Line: {train['Line']} | Arrival: {train['Arrival']} min | Alert: {train['ALERT']}")

            if train["ALERT"] is True and bullet_alert_flag is True:
                if train["FLASH"]:
                    if (now >= train["PREV_TIME"] + train["FLASH_OFF"]):
                        self.prev_time = now
                        mta_bullets[0,row] = bullet_index["ALERT"]
                        self.alert_flash = False

                elif train["FLASH"] is False:
                    if (now >= train["PREV_TIME"] + train["FLASH_ON"]):
                        self.prev_time = now
                        mta_bullets[0,row] = bullet_index[train["Line"]]
                        self.alert_flash = True
            else:
                mta_bullets[0,row] = bullet_index[train["Line"]]

        if rows == 1:
            mta_bullets[0,1] = bullet_index["MTA"]
            arrival_label_2.text = "-1"

    def alert_text(self, arrival_data):
        if arrival_data is None or arrival_data["alerts"] == []:
            return "No active alerts."

        i = 1
        alert_string = ""
        for alert in arrival_data["alerts"]:
            alert_string += "{num}.{alert_txt} ".format(num=str(i), alert_txt=alert)
            i += 1

        return alert_string

def display_alt_text():
    arrival_label_2.text = ""
    weather_label.text = ""
    mta_bullets[0,1] = bullet_index["BLANK"]

def scroll(line):
    line.x = line.x - 1
    line_width = line.bounding_box[2]
    #print("Scrolling - x:", line.x, "y:", line.y, "width:", line_width)
    if line.x < -line_width:
        line.x = display.width
        return "DONE"
    #display.refresh(minimum_frames_per_second=0)
    return None

def update_time(*, hours=None, minutes=None, show_colon=False):
    now = time.localtime()  # Get the time values we need
    if hours is None:
        hours = now[3]
    #if hours >= 18 or hours < 6:  # evening hours to morning
    #    clock_label.color = color[1]
    #else:
    clock_label.color = color[3]  # daylight hours

    if minutes is None:
        minutes = now[4]

    clock_label.text = "{hours:02d}:{minutes:02d}".format(
        hours=hours, minutes=minutes)

    if DEBUG:
        print("Label x: {} y: {}".format(clock_label.x, clock_label.y))

def change_screen():
    default_group.hidden = not default_group.hidden
    arrivals_group.hidden = not arrivals_group.hidden

clock_check = None
weather_refresh = None
aqi_refresh = None
subway_refresh = None
alert_refresh = None
bullet_alert_flag = True
return_to_default = None
displayed_alert_text = " "
alert_text = " "
api_fails = 0

update_time(show_colon=True)  # Display whatever time is on the board
arrivals = Arrivals()
atmosphere = Atmosphere()

default_group = displayio.Group()
arrivals_group = displayio.Group()

default_group.append(clock_label)  # ELEMENT 1 add the clock label to the default_group
default_group.append(mta_bullets)      #ELEMENT 2
default_group.append(aqi_lvl)      #ELEMENT 3
default_group.append(weather_label) #ELEMENT 4
default_group.append(aqi_label)     #ELEMENT 5
default_group.append(arrival_label_1) #ELEMENT 6
default_group.append(arrival_label_2) #ELEMENT 7
default_group.append(alert_scroll_label) #ELEMENT 8

arrivals_group.append(arrivals_row_nums)
arrivals_group.append(arrivals_north_bullets)
arrivals_group.append(arrivals_south_bullets)
arrivals_group.append(arrivals_north_arrow)
arrivals_group.append(arrivals_south_arrow)
arrivals_group.append(north_rectangle)
arrivals_group.append(south_rectangle)
arrivals_group.append(arrivals_north_label)
arrivals_group.append(arrivals_south_label)
arrivals_group.append(mins_tile)

root_group.append(default_group)
root_group.append(arrivals_group)

default_group.hidden = False
arrivals_group.hidden = True

while True:
    gc.collect()
    event = keys.events.get()

    if clock_check is None or time.monotonic() > clock_check + 3600:
        try:
            update_time(show_colon=True)
            network.get_local_time()  # Synchronize board's clock to Internet
        except RuntimeError as e:
            print("CLOCK UPDATE ERROR:", e)

        clock_check = time.monotonic()

    if weather_refresh is None or time.monotonic() > weather_refresh + 600:
        try:
            atmosphere.weather_api()
        except Exception as e:
            print("WEATHER API ERROR:", e)

        weather_refresh = time.monotonic()

    if aqi_refresh is None or time.monotonic() > aqi_refresh + 900:
        try:
            atmosphere.aqi_api()
        except Exception as e:
            print("AQI API ERROR:", e)

        aqi_refresh = time.monotonic()

    if subway_refresh is None or time.monotonic() > subway_refresh + 12:
        if not arrivals_group.hidden:
            arrivals.scroll_board_directions()

        try:
            arrival_data = arrivals.api_call()

        except Exception as e:
            print(f"ERROR in subway_refresh: {e}")
            arrival_data = None

        if arrival_data is None:
            api_fails += 1
        else:
            api_fails = 0

        if api_fails > 5:
            print("API STUCK IN DOOM LOOP, RESET TIME~!")
            clock_label.text = "reset"
            time.sleep(120)
            supervisor.reload()

        alert_text = arrivals.alert_text(arrival_data)
        alert_scroll_label.text = alert_text
        if alert_text != displayed_alert_text:
            bullet_alert_flag = True

        subway_refresh = time.monotonic()

    if event:
        scroll_check = None
        if event.pressed and event.key_number == 1: #DOWN button
            display_alt_text()
            bullet_alert_flag = False
            displayed_alert_text = alert_text
            while scroll_check != "DONE":
                scroll_check = scroll(alert_scroll_label)
                time.sleep(0.02)

        elif event.pressed and event.key_number == 0: #UP button
            change_screen()
            if default_group.hidden:
                return_to_default = time.monotonic()

    if not arrivals_group.hidden:
        arrivals.update_board(arrival_data)
        if time.monotonic() > return_to_default + 1200:
            change_screen()

    if not default_group.hidden:
        arrivals.update_display(arrival_data, bullet_alert_flag, now=time.monotonic())
        update_time()
        atmosphere.update_display()

    time.sleep(0.5)
