# This file is where you keep secret settings, passwords, and tokens!
# If you put them in the code you risk committing that info or sharing it

secrets = {
    "ssid": "",  # wifi network name
    "password": "",  # wifi password
    "timezone": "",  # IANA time zone name, e.g. America/Los_Angeles (list: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)
    "openweather_key": "",  # api key from https://openweathermap.org/api
    "iqair_key": "",  # api key from https://www.iqair.com/us/air-quality-monitors/api
    "aio_username": "",  # Adafruit IO username from https://io.adafruit.com; the account is only used to set the clock
    "aio_key": "",  # Adafruit IO Active Key
    "latitude": "",  # latitude where unit is located
    "longitude": "",  # longitude where unit is located
    "default_direction": "",  # "North" or "South". These are BART's route labels, not compass directions: see README
    "bart_station": "",  # four-letter station abbreviation, e.g. "16TH". Full list in README
    "bart_lines": "",  # optional: line colors to show, comma separated, e.g. "RED,YELLOW". Empty shows every line at the station
    "bart_key": "MW9S-E7SL-26DU-VV8V",  # BART's public key. Register your own (free) at https://api.bart.gov/api/register.aspx
}
