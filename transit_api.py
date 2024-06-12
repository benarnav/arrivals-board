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
    def __init__(self) -> None:
        self.urls = {
            "A,C,E": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace",
            "B,D,F,M": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm",
            "G": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g",
            "J,Z": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz",
            "N,Q,R,W": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw",
            "L": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l",
            "1,2,3,4,5,6,7": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",
            "SIR": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-si",
        }
        self.feed = gtfs_realtime_pb2.FeedMessage()

    def get_arrivals(self, station_ids, subway_lines):
        arrivals_data = {"North": [], "South": [], "alerts": []}

        for line in subway_lines:
            for url in self.urls:
                if line in url:
                    response = requests.get(self.urls[url])
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
        url = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Fsubway-alerts.json"
        response = requests.get(url)
        active_alerts = []
        now = int(time.time())

        if response.status_code == 200:
            alert_data = response.json()
            for alert in alert_data["entity"]:
                for alert_time in alert["alert"]["active_period"]:
                    try:
                        if alert_time["start"] < now and alert_time["end"] > now:
                            affected_line = alert["alert"]["informed_entity"][0][
                                "route_id"
                            ]
                            if affected_line in subway_lines:
                                # print(alert['alert']['header_text']['translation'][0]['text'])
                                alert_text = alert["alert"]["header_text"][
                                    "translation"
                                ][0]["text"].replace("\n", " ")
                                alert_text = alert_text.replace("  ", " ")
                                active_alerts.append((affected_line, alert_text))
                    except:
                        continue
        else:
            error_msg = f"Error: {response.status_code} - {response.text}"
            return error_msg

        return active_alerts


class WMATA:
    def __init__(self, wmata_key) -> None:
        self.headers = {
            "api_key": wmata_key,
        }
        self.feed = gtfs_realtime_pb2.FeedMessage()
        self.directions = {0: "NE", 1: "SW"}

    def get_arrivals(self, station_ids, lines):
        response = requests.get(
            "https://api.wmata.com/gtfs/rail-gtfsrt-tripupdates.pb",
            headers=self.headers,
        )
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
                            trip_data["NE-SW"] = self.directions[
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
        r = requests.get(
            "https://api.wmata.com/Incidents.svc/json/Incidents", headers=self.headers
        )
        alert_data = []
        try:
            alerts = r.json()
            if alerts["Incidents"] != []:
                for alert in alerts:
                    for line in lines:
                        if line in alert["Description"].upper():
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
        subway_lines = list(args["subway-lines"].split(","))
        station_ids = list(args["station-ids"].split(","))

        if not validate_api_key(api_key):
            return {"error": "Invalid API key"}, 401  # Unauthorized

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
        station_ids = list(args["station-ids"].split(","))
        if args["lines"] is not None and args["lines"] != []:
            lines = list(args["lines"].split(","))
            lines = [line.upper() for line in lines]
        else:
            lines = []
            for station in station_ids:
                lines += wmata_stations[station]["Lines"]

        if not validate_api_key(api_key):
            return {"error": "Invalid API key"}, 401  # Unauthorized

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
