# This file is where you keep secret settings, passwords, and tokens!
# If you put them in the code you risk committing that info or sharing it

secrets = {
    "ssid": "",  # wifi network name
    "password": "",  # wifi password
    "timezone": "",  # http://worldtimeapi.org/timezones e.g. America/New_York
    "openweather_key": "",  # api key from https://openweathermap.org/api
    "iqair_key": "",  # api key from https://www.iqair.com/us/air-quality-monitors/api
    "aio_username": "",  # username from https://accounts.adafruit.com/users/sign_in
    "aio_key": "",  # adafruit key
    "latitude": "",  # latitude where unit is located
    "longitude": "",  # longitude where unit is located
    "default_direction": "",  # "North" or "South"
    "station_ids": "",  # Required. GTFS stop ids WITH their N/S suffix, comma separated, e.g. "A41N,A41S". Find them in stops.txt from http://web.mta.info/developers/data/nyct/subway/google_transit.zip
    "lines": "",  # Required. Subway lines to show, comma separated, e.g. "A,C" or "2,3", using the feed's ids: SI for Staten Island Railway, GS / FS / H for the 42 St, Franklin Av and Rockaway shuttles. Lines at different stations work as long as their station ids are listed above.
}
