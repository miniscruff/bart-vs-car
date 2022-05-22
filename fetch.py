import requests
import os
import json
import time
from itertools import permutations
from dotenv import load_dotenv
from progressbar import ProgressBar, Counter, Percentage, Bar

load_dotenv()  # take environment variables from .env.

# some consts
OUTPUT_FILE = "data.json"
MANUAL_FILE = "manual.json"
SLEEP_TIMER = 0.25

# API Keys
BART_API_KEY = os.getenv("BART_API_KEY")
GRAPH_HOPPER_API_KEY = os.getenv("GRAPH_HOPPER_API_KEY")

if BART_API_KEY is None:
    print("missing bart api key")
    exit(1)

if GRAPH_HOPPER_API_KEY is None:
    print("missing graph hopper api key")
    exit(1)

def request_json(url, params, *json_path):
    r = requests.get(url, params=params)
    ret = r.json()
    for path in json_path:
        ret = ret[path]
    return ret

def create_bart_fare_args(orig, dest):
    return {
        'key': BART_API_KEY,
        'cmd': 'fare',
        'orig': orig,
        'dest': dest,
        'json': 'y',
    }

def get_stations():
    return request_json(
        'http://api.bart.gov/api/stn.aspx',
        {
            'key': BART_API_KEY,
            'cmd': 'stns',
            'json': 'y',
        },
        "root", "stations", "station",
    )

def get_route_fare(orig, dest):
    fare_str = request_json(
        'http://api.bart.gov/api/sched.aspx',
        {
            'key': BART_API_KEY,
            'cmd': 'fare',
            'json': 'y',
            'orig': orig,
            'dest': dest,
        },
        "root", "trip", "fare",
    )
    return int(fare_str.replace(".", ""))

def get_car_data(start_lat, start_long, end_lat, end_long):
    return request_json(
        'https://graphhopper.com/api/1/route',
        {
            'key': GRAPH_HOPPER_API_KEY,
            'instructions': False,
            'point': [f'{start_lat},{start_long}', f'{end_lat},{end_long}'],
        },
        "paths", 0,
    )

def dict_merge(dct, merge_dct):
    """ Recursive dict merge. Inspired by :meth:``dict.update()``, instead of
    updating only top-level keys, dict_merge recurses down into dicts nested
    to an arbitrary depth, updating keys. The ``merge_dct`` is merged into
    ``dct``.
    :param dct: dict onto which the merge is executed
    :param merge_dct: dct merged into dct
    :return: None
    """
    for k in merge_dct:
        if (k in dct and isinstance(dct[k], dict) and isinstance(merge_dct[k], dict)):  #noqa
            dict_merge(dct[k], merge_dct[k])
        else:
            dct[k] = merge_dct[k]

def main():
    data = {}

    # some data is manual configured such as parking costs
    with open(MANUAL_FILE) as manual:
        manual_data = json.load(manual)

    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as output:
            data = json.load(output)

    dict_merge(data, manual_data)

    if "name" not in data["stations"]["12TH"]:
        for station in get_stations():
            data["stations"][station["abbr"]] = {
                "name": station["name"],
                "abbr": station["abbr"],
                "lat": station["gtfs_latitude"],
                "long": station["gtfs_longitude"],
                "address": station["address"],
                "city": station["city"],
                "county": station["county"],
                "zipcode": station["zipcode"],
            }

    for orig, dest in permutations(data["stations"].keys(), 2):
        if "routes" not in data:
            data["routes"] = {}

        if orig not in data["routes"]:
            data["routes"][orig] = {}

        if dest not in data["routes"][orig]:
            data["routes"][orig][dest] = {
                "fare": None,
                "car_time": None,
                "car_distance": None,
            }


    widgets = [
        Counter(), ' ',
        Percentage(), ' ',
        Bar(), ' ',
    ]

    station_perms = permutations(data["stations"].keys(), 2)
    station_count = len(data["stations"])
    max_value = station_count * (station_count-1)
    count = 0
    last_update = 0
    with ProgressBar(widgets=widgets, max_value=max_value) as bar:
        for orig, dest in station_perms:
            route = data["routes"][orig][dest]

            if route["car_time"] is None:
                car_data = get_car_data(
                    data["stations"][orig]["lat"],
                    data["stations"][orig]["long"],
                    data["stations"][dest]["lat"],
                    data["stations"][dest]["long"],
                )
                # time is in milliseconds, convert it to seconds
                route["car_time"] = car_data["time"]*0.001
                # distance is in meters, so convert that to miles
                route["car_distance"] = car_data["distance"]*0.000621371
                last_update += 1
                time.sleep(SLEEP_TIMER)

            if route["fare"] is None:
                # fare is in cents
                route["fare"] = get_route_fare(orig, dest)
                # cost from A to B is the same as B to A
                data["routes"][dest][orig]["fare"] = route["fare"]
                last_update += 1
                time.sleep(SLEEP_TIMER)

            # occasionally save our data in case we need to restart
            if last_update > 20:
                with open(OUTPUT_FILE, 'w') as output:
                    json.dump(data, output, indent=2, sort_keys=True)
                last_update = 0

            count += 1
            bar.update(count)

    with open(OUTPUT_FILE, 'w') as output:
        json.dump(data, output, sort_keys=True)

if __name__ == '__main__':
    main()
