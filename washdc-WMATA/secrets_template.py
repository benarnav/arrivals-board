# This file is where you keep secret settings, passwords, and tokens!
# If you put them in the code you risk committing that info or sharing it

secrets = {
    'ssid' : '', #wifi network name
    'password' : '', #wifi password
    'timezone' : '', # http://worldtimeapi.org/timezones
    'openweather_key' : '', #api key from https://openweathermap.org/api
    'iqair_key' : '', #api key from https://www.iqair.com/us/air-quality-monitors/api
    'aio_username' : '', #username from https://accounts.adafruit.com/users/sign_in
    'aio_key' : '', #adafruit key
    'latitude' : '', #latitude where unit is located
    'longitude' : '', #latitude where unit is located
    'default_direction': '', #Pick either NE or SW, directions based on rough direction of travel
    'transit_url': '', #url to your api endpoint on pythonganywhere or other host
    'transit_headers' : {'api-key': '', #api key for Flask app
                         'lines': [], #optional: specify lines to be displayed, if not included will default to show all lines in station_ids
                         'station_ids': "", #station code from https://developer.wmata.com/docs/services/5476364f031f590f38092507/operations/5476364f031f5909e4fe3311?
                         }                  #For multiple stations (eg L'Enfant Plaza), separate with comma and no spaces
                   
    }
