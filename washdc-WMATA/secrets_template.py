# This file is where you keep secret settings, passwords, and tokens!
# If you put them in the code you risk committing that info or sharing it

secrets = {
    "ssid": "",  # wifi network name
    "password": "",  # wifi password
    "timezone": "",  # IANA time zone name, e.g. America/New_York (list: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)
    "openweather_key": "",  # api key from https://openweathermap.org/api
    "iqair_key": "",  # api key from https://www.iqair.com/us/air-quality-monitors/api
    "aio_username": "",  # Adafruit IO username from https://io.adafruit.com; the account is only used to set the clock
    "aio_key": "",  # Adafruit IO Active Key
    "latitude": "",  # latitude where unit is located
    "longitude": "",  # longitude where unit is located
    "rotation": "",  # optional: 180 to hang the unit upside down, which moves the board and its power cable to the other side; empty or 0 as built
    "sleep": "",  # optional: "on" turns the display off overnight; UP or DOWN turns it back on for 20 minutes
    "sleep_start": "",  # when it turns off, 24-hour HH:MM; empty means 22:00
    "sleep_end": "",  # when it turns back on, 24-hour HH:MM; empty means 06:00
    "default_direction": "",  # "NE" or "SW", the rough direction of travel
    "wmata_key": "",  # api key from https://developer.wmata.com (the free Default Tier is plenty)
    "station_ids": "",  # Required. Station codes from the WMATA developer portal, comma separated, e.g. "A01,C01" for both levels of Metro Center
    "lines": "",  # optional: lines to show, comma separated, e.g. "blue,silver". Empty shows every line at the station
}
