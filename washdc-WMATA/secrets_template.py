# This file is where you keep secret settings, passwords, and tokens!
# If you put them in the code you risk committing that info or sharing it

secrets = {
    "ssid": "",  # wifi network name
    "password": "",  # wifi password
    "timezone": "",  # http://worldtimeapi.org/timezones
    "openweather_key": "",  # api key from https://openweathermap.org/api
    "iqair_key": "",  # api key from https://www.iqair.com/us/air-quality-monitors/api
    "aio_username": "",  # username from https://accounts.adafruit.com/users/sign_in
    "aio_key": "",  # adafruit key
    "latitude": "",  # latitude where unit is located
    "longitude": "",  # latitude where unit is located
    "default_direction": "",  # Pick either NE or SW, directions based on rough direction of travel
    "transit_url": "",  # url to your api endpoint on pythonganywhere or other host e.g. https://YOURUSERNAME.pythonanywhere.com/api/wmata-arrivals
    "transit_headers": {
        "api-key": "",  # api key for Flask app
        "lines": "",  # optional: specify lines to be displayed, if not included will default to show all lines in station-ids. NB: write lines separated by commas WITHOUT spaces. eg: "blue,silver"
        "station-ids": "",  # station code from the WMATA developer portal or search in `station_dict.py`
    },  # For multiple stations (eg L'Enfant Plaza), separate with comma and no spaces
}
