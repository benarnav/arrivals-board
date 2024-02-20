# This file is where you keep secret settings, passwords, and tokens!
# If you put them in the code you risk committing that info or sharing it

secrets = {
    'ssid' : '', #wifi network name
    'password' : '', #wifi password
    'timezone' : '', # http://worldtimeapi.org/timezones
    'api_key' : '', #MTA api key from https://api.mta.info/
    'openweather_key' : '', #api key from https://openweathermap.org/api
    'iqair_key' : '', #api key from https://www.iqair.com/us/air-quality-monitors/api
    'aio_username' : '', #username from https://accounts.adafruit.com/users/sign_in
    'aio_key' : '', #adafruit key
    'latitude' : '', #latitude where unit is located
    'longitude' : '', #latitude where unit is located
    'transit_url' : '', #url to your api endpoint on pythonganywhere or other host
    'transit_headers' : [{'api-key': '', #MTA api key from https://api.mta.info/
                          'user-station': "", #local station, for multiple stations, add another dict to this list 
                          'user-station-ids': "", #optional
                          'subway-lines': ""} #Subway lines to be displayed, separated by a comma and no spaces
    ]}
