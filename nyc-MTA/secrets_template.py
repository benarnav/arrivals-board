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
    "transit_url": "",  # url to your api endpoint on pythonganywhere or other host e.g. https://YOURUSERNAME.pythonanywhere.com/api/mta-arrivals
    "transit_headers": [
        {
            "api-key": "",  # api key for Flask app
            "station-ids": "",  # required, find ids in `station_dict.py` or the stops.txt from http://web.mta.info/developers/data/nyct/subway/google_transit.zip
            "subway-lines": "",  # Subway lines to be displayed, separated by a comma and WITHOUT spaces. eg: "2,3" or "N,R"
        } 
    ], # For multiple stations, add an additional dictionary to this list
}  
