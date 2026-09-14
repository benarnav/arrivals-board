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
    "default_direction": "",  # "North" or "South"
    "station_ids": "",  # Required. GTFS stop ids WITH their N/S suffix, comma separated, e.g. "A41N,A41S". Find them in stops.txt from http://web.mta.info/developers/data/nyct/subway/google_transit.zip
    "lines": "",  # Required. Subway lines to show, comma separated, e.g. "A,C" or "2,3", using the feed's ids: SI for Staten Island Railway, GS / FS / H for the 42 St, Franklin Av and Rockaway shuttles. Lines at different stations work as long as their station ids are listed above.
}
