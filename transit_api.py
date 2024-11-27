from envar import envar
from flask import Flask
from flask_restful import Resource, Api, reqparse
from google.transit import gtfs_realtime_pb2
from station_dict import mta_stations, wmata_stations
import requests
import time

app = Flask(__name__)
api = Api(app)


def validate_api_key(api_key):
    expected_api_key = envar["api_key"]
    return api_key == expected_api_key


class MTA:
    ARRIVAL_URLS = {
            "A,C,E": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace",
            "B,D,F,M": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm",
            "G": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g",
            "J,Z": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz",
            "N,Q,R,W": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw",
            "L": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l",
            "1,2,3,4,5,6,7": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",
            "SIR": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-si",
        }
    ALERTS_URL = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Fsubway-alerts.json"
    def __init__(self) -> None:
        self.feed = gtfs_realtime_pb2.FeedMessage()
        
    def get_arrivals(self, station_ids, subway_lines):
        arrivals_data = {"North": [], "South": [], "alerts": []}

        for line in subway_lines:
            for url in MTA.ARRIVAL_URLS:
                if line in url:
                    response = requests.get(MTA.ARRIVAL_URLS[url])
                    self.feed.ParseFromString(response.content)
                    now = time.time()
                    for entity in self.feed.entity:
                        if entity.HasField("trip_update"):
                            if entity.trip_update.trip.route_id in subway_lines:
                                for station in entity.trip_update.stop_time_update:
                                    trip_data = {
                                        "Line": "",
                                        "N-S": "",
                                        "Direction": "",
                                        "Arrival": "",
                                    }

                                    if station.stop_id in station_ids:
                                        arrival = (station.arrival.time - now) / 60
                                        if arrival < 0 or arrival > 200:
                                            continue
                                        trip_data["Line"] = (
                                            entity.trip_update.trip.route_id
                                        )
                                        trip_data["N-S"] = station.stop_id[-1]
                                        trip_data["Direction"] = mta_stations[
                                            entity.trip_update.stop_time_update[
                                                -1
                                            ].stop_id
                                        ]
                                        if arrival < 1.0:
                                            trip_data["Arrival"] = 0
                                        else:
                                            trip_data["Arrival"] = round(arrival)
                                    if trip_data["N-S"] == "N":
                                        arrivals_data["North"].append(trip_data)
                                    elif trip_data["N-S"] == "S":
                                        arrivals_data["South"].append(trip_data)

        for direction, trains in arrivals_data.items():
            sorted_trains = sorted(trains, key=lambda train: train["Arrival"])
            if direction == "North":
                arrivals_data["North"] = sorted_trains[:11]
            elif direction == "South":
                arrivals_data["South"] = sorted_trains[:11]

        return arrivals_data

    def get_alerts(self, subway_lines):
        now = int(time.time())

        try:
            response = requests.get(MTA.ALERTS_URL, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            active_alerts = []
            for alert in data.get("entity", []):
                try:
                    alert_info = alert["alert"]
                    route_id = alert_info["informed_entity"][0]["route_id"]
                    
                    if route_id not in subway_lines:
                        continue
                        
                    for period in alert_info["active_period"]:
                        if period["start"] < now < period["end"]:
                            alert_text = alert_info["header_text"]["translation"][0]["text"]
                            active_alerts.append((route_id, alert_text.replace("\n", " ").strip()))
                            break
                            
                except (KeyError, IndexError) as e:
                    print(f"Error parsing response: {str(e)}")
                    continue
                    
            return active_alerts
            
        except requests.RequestException as e:
            print(f"Error: {str(e)}")
            return
        except ValueError as e:
            print(f"Error parsing response: {str(e)}")
            return


class WMATA:
    ARRIVALS_URL="https://api.wmata.com/gtfs/rail-gtfsrt-tripupdates.pb"
    ALERTS_URL="https://api.wmata.com/Incidents.svc/json/Incidents"
    DIRECTIONS = {0: "NE", 1: "SW"}
    LINE_CODES = {"GR":"GREEN",
                "OR":"ORANGE",
                "RD":"RED",
                "SV":"SILVER",
                "BL":"BLUE",
                "YL":"YELLOW"}
    def __init__(self, wmata_key) -> None:
        self.headers = {
            "api_key": wmata_key,
        }
        self.feed = gtfs_realtime_pb2.FeedMessage()
        

    def get_arrivals(self, station_ids, lines):
        response = requests.get(WMATA.ARRIVALS_URL,headers=self.headers)
        self.feed.ParseFromString(response.content)
        arrivals_data = {"NE": [], "SW": [], "alerts": []}

        now = time.time()

        for entity in self.feed.entity:
            if entity.HasField("trip_update"):
                if entity.trip_update.trip.route_id in lines:
                    for station in entity.trip_update.stop_time_update:
                        trip_data = {
                            "Line": "",
                            "NE-SW": "",
                            "Direction": "",
                            "Arrival": "",
                        }
                        if station.stop_id[3:6] in station_ids:
                            arrival = (station.arrival.time - now) / 60
                            if arrival < 0 or arrival > 200:
                                continue
                            trip_data["Line"] = entity.trip_update.trip.route_id
                            trip_data["NE-SW"] = WMATA.DIRECTIONS[
                                entity.trip_update.trip.direction_id
                            ]
                            trip_data["Direction"] = wmata_stations[
                                entity.trip_update.stop_time_update[-1].stop_id[3:6]
                            ]["Name"]
                            if arrival < 1.0:
                                trip_data["Arrival"] = 0
                            else:
                                trip_data["Arrival"] = round(arrival)

                            if trip_data["NE-SW"] == "NE":
                                arrivals_data["NE"].append(trip_data)
                            elif trip_data["NE-SW"] == "SW":
                                arrivals_data["SW"].append(trip_data)

        for direction, trains in arrivals_data.items():
            sorted_trains = sorted(trains, key=lambda train: train["Arrival"])
            if direction == "NE":
                arrivals_data["NE"] = sorted_trains[:11]
            elif direction == "SW":
                arrivals_data["SW"] = sorted_trains[:11]

        return arrivals_data

    def get_alerts(self, lines):
        r = requests.get(WMATA.ALERTS_URL, headers=self.headers)
        alert_data = []
        try:
            alerts = r.json()
            if alerts["Incidents"] != []:
                for alert in alerts["Incidents"]:
                    affected_lines = set([WMATA.LINE_CODES[l] for l in alert["LinesAffected"].split(";") if l])
                    matching_lines = affected_lines & lines 
                    if matching_lines:
                        for line in matching_lines:
                            alert_data.append((line, alert["Description"]))

        except Exception as e:
            return f"Alerts Error: {e}"

        return alert_data


class MTA_ArrivalsResource(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument(
            "api-key",
            type=str,
            required=True,
            help="API key is required",
            location="headers",
        )
        parser.add_argument(
            "station-ids",
            type=str,
            location="headers",
            required=True,
            help="At least one station id is required",
        )
        parser.add_argument(
            "subway-lines",
            type=str,
            location="headers",
            required=True,
            help="At least one subway line is required",
        )

        args = parser.parse_args()
        api_key = args["api-key"]
        if not validate_api_key(api_key):
            return {"error": "Invalid API key"}, 401  # Unauthorized
        subway_lines = {l.strip() for l in args["subway-lines"].split(",")}
        station_ids = {id.strip() for id in args["station-ids"].split(",")}
      
        mta = MTA()
        arrivals = mta.get_arrivals(station_ids=station_ids, subway_lines=subway_lines)

        arrivals["alerts"] = mta.get_alerts(subway_lines)

        return arrivals


class WMATA_ArrivalsResource(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument(
            "api-key",
            type=str,
            required=True,
            help="API key is required",
            location="headers",
        )
        parser.add_argument(
            "station-ids",
            type=str,
            location="headers",
            required=True,
            help="At least one station id is required",
        )
        parser.add_argument("lines", type=str, location="headers")

        args = parser.parse_args()
        api_key = args["api-key"]
        if not validate_api_key(api_key):
            return {"error": "Invalid API key"}, 401  # Unauthorized
        
        station_ids = set(args["station-ids"].split(","))
        lines = (
                {l.strip().upper() for l in args["lines"].split(",")} 
                if args.get("lines")
                else {line for station in station_ids for line in wmata_stations[station]["Lines"]}
                )

        wmata_key = envar["wmata_key"]
        wmata = WMATA(wmata_key)
        arrivals = wmata.get_arrivals(station_ids, lines)

        arrivals["alerts"] = wmata.get_alerts(lines)

        return arrivals


api.add_resource(MTA_ArrivalsResource, "/api/mta-arrivals")
api.add_resource(WMATA_ArrivalsResource, "/api/wmata-arrivals")


@app.route("/")
def index():
    return "This is not for you"


if __name__ == "__main__":
    app.run(debug=False)
