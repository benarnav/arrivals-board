#from dotenv import load_dotenv
from envar import envar
from nyct_gtfs import NYCTFeed
from flask import Flask, jsonify
from datetime import datetime
from flask_restful import Resource, Api, reqparse
import requests
import time

app = Flask(__name__)
api = Api(app)

def validate_api_key(api_key):
    expected_api_key = envar["api_key"] #os.getenv("api_key")
    return api_key == expected_api_key

def get_arrivals(trains, user_station, line):
    station_arrivals = []
    for train in trains:
        current_trip = {}
        if train.stop_time_updates == []:
            continue
        current_trip["Line"] = line
        current_trip["N-S"] = train.direction
        current_trip["Direction"] = train.stop_time_updates[-1].stop_name
        current_trip["Delay"] = train.has_delay_alert
        for station in train.stop_time_updates:
            if station.stop_name is not None:
                if user_station in station.stop_name:
                    now = datetime.now()
                    time_difference = station.arrival - now
                    hours, remainder = divmod(time_difference.seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    if hours == 0 and minutes == 0:
                        current_trip["Arrival"] = 0
                    else:
                        current_trip["Arrival"] = (hours*60) + minutes + (min(1, (seconds + 29) // 60)) #f"{minutes}:{seconds}"
                    if current_trip["Arrival"] == 1440:
                        continue
                    station_arrivals.append(current_trip)

    return station_arrivals

def get_alerts(subway_lines, mta_key):
    url = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Fsubway-alerts.json"
    headers = {'x-api-key': mta_key}
    response = requests.get(url, headers=headers)
    active_alerts = []
    now = int(time.time())

    if response.status_code == 200:
        alert_data = response.json()
        for alert in alert_data['entity']:
            for alert_time in alert['alert']['active_period']:
                try:
                    if alert_time['start'] < now and alert_time['end'] > now:
                        if alert['alert']['informed_entity'][0]['route_id'] in subway_lines:
                            #print(alert['alert']['header_text']['translation'][0]['text'])
                            alert_text = alert['alert']['header_text']['translation'][0]['text'].replace("\n", " ")
                            alert_text = alert_text.replace("  ", " ")
                            active_alerts.append((alert['alert']['informed_entity'][0]['route_id'], alert_text))

                except:
                    #print('No End Time')
                    continue
    else:
        error_msg = f"Error: {response.status_code} - {response.text}"
        return error_msg

    return active_alerts


class SubwayArrivalsResource(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('api-key', type=str, required=True, help='API key is required', location='headers')
        parser.add_argument('user-station', type=str, location='headers', required=True, help='At least one station name is required')
        parser.add_argument('user-station-ids', type=str, location='headers')
        parser.add_argument('subway-lines', type=str, location='headers', required=True, help='At least one subway line is required')

        args = parser.parse_args()
        api_key = args['api-key']
        user_station = args['user-station']
        subway_lines = list(args['subway-lines'].split(','))
        if args['user-station-ids'] is not None:
            user_station_ids = list(args['user-station-ids'].split(','))
        else:
            user_station_ids = None

        if not validate_api_key(api_key):
            return {'error': 'Invalid API key'}, 401  # Unauthorized

        mta_key = envar["mta_key"]
        arrival_info = []

        active_alerts = get_alerts(subway_lines=subway_lines, mta_key=mta_key)

        for subway_line in subway_lines:
            feed = NYCTFeed(subway_line, api_key=mta_key)
            trains = feed.filter_trips(line_id=subway_line, headed_for_stop_id=user_station_ids)
            arrival_info = arrival_info + get_arrivals(trains, user_station, subway_line)

        arrival_info_sorted = sorted(arrival_info, key=lambda x: x["Arrival"])

        for_transmission = {}
        for_transmission["North"] =[entry for entry in arrival_info_sorted if entry['N-S'] == 'N']
        for_transmission["South"] =[entry for entry in arrival_info_sorted if entry['N-S'] == 'S']

        for_transmission["North"] = for_transmission["North"][:11]
        for_transmission["South"] = for_transmission["South"][:11]

        for_transmission['alerts'] = active_alerts

        return for_transmission

api.add_resource(SubwayArrivalsResource, '/api/subway-arrivals')

@app.route('/')
def index():
    return "This is not for you"

if __name__ == '__main__':
    app.run(debug=True)
