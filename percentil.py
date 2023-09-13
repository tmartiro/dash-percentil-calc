#!/usr/bin/env python3

import requests
import os
import pickle
import json

from datetime import datetime
import argparse

# Default values 
base_url = 'https://localhost:9000'
user = 'test'
password = 'secret'
session = None
session_file = 'session_data.pkl'


# Parse arguments

parser = argparse.ArgumentParser(description='Calculate the 95th percentile for the dashboard graphs.')
parser.add_argument('-f', type=str, help='from date, format "Year-Month-Day Hour:Min:Sec", example 2023-09-13 14:30:00', required=True)
parser.add_argument('-u',type=str, help='until date, format "Year-Month-Day Hour:Min:Sec", example 2023-09-13 14:30:00', required=True)
args = parser.parse_args()

from_date = args.f
until_date = args.u

# Convert the date string to a datetime object
from_obj = datetime.strptime(from_date, "%Y-%m-%d %H:%M:%S")
until_obj = datetime.strptime(until_date, "%Y-%m-%d %H:%M:%S")

# Define the reference date (e.g., the epoch)
now_date = datetime.now()

# Calculate the time difference between the date and the reference date
fromDate = from_obj - now_date
untilDate = until_obj - now_date

# Calculate the total number of minutes
fromDateMins = int(fromDate.total_seconds() / 60)
untilDateMins = int(untilDate.total_seconds() / 60)

print(f"Calculate 95th percentil for the following time range: {fromDateMins}min to {untilDateMins}min")

# Parse environment variables
if os.environ.get('USER') is not None:
    user = os.environ.get('USER')

if os.environ.get('PASS') is not None:
    password = os.environ.get('PASS')

if os.environ.get('URL') is not None:
    base_url = os.environ.get('URL')

# Endpoints
auth_url = "%s/api/auth" % base_url
graphboard_url = "%s/api/graphboards" % base_url
graphite_url = "%s/api/graphite" % base_url

def format_bandwidth(value):
    if value < 1e3:
        return f"{value:.2f} bit/s"
    elif value < 1e6:
        return f"{(value / 1e3):.2f} Kbit/s"
    elif value < 1e9:
        return f"{(value / 1e6):.2f} Mbit/s"
    else:
        return f"{(value / 1e9):.2f} Gbit/s" 

def getPercentil(session, params):
    response = session.post(graphite_url, params=params)
    return response

# Load session key
try:
    with open(session_file, 'rb') as f:
        session = pickle.load(f)
except Exception as e:
    pass


# Check whether the session is valid
if session is not None:
    response = session.get(auth_url)
    if response.status_code > 300:
        session = None

if session is None:
    # Create a session to persist cookies across requests
    session = requests.Session()
    login_data = { 'user': user, 'password': password }

    # Perform the login by sending a POST request with the login data
    response = session.post(auth_url, json=login_data)

    if response.status_code >= 200 and response.status_code < 300:
        with open(session_file, 'wb') as f:
            pickle.dump(session, f)
    else:
        print("ERROR: authentication failed: %s" % response)
        exit(1)

# Get dashboards
response = session.get(graphboard_url)
if response.status_code >= 200 and response.status_code < 300:
    dashboards = []
    data = response.json()
    if 'data' in data:
        data = data["data"]
    if 'dashboards' in data:
        for dash in data["dashboards"]:
            print("- %s" % dash['name'])
            if 'data' in dash:
                charts = json.loads(dash['data'])
                for chart in charts:
                    print("")
                    print("  * %s" % chart["mTitle"])
                    if 'mMembers' in chart:
                        members = chart['mMembers']
                        members_octet_tx = []
                        members_octet_rx = []
                        for m in members:
                            vlan = ""
                            iface = m['interface']
                            sw = m['switch']

                            
                            if m['vlan_id'] is not None and m['vlan_id'] != "":
                                vlan = "_%s" % m['vlan_id']

                            if iface is None or sw is None:
                                continue

                            if "." in m['interface']:
                                vlan = ""
                                iface = iface.replace('.','_')

                            print("      %s.interface-%s%s" % (sw, iface, vlan))
                            members_octet_tx.append("collectd.%s.interface-%s%s.if_octets.tx" % (sw, iface, vlan))
                            members_octet_rx.append("collectd.%s.interface-%s%s.if_octets.rx" % (sw, iface, vlan))
                        
                        if len(members_octet_rx) > 0 and len(members_octet_tx) > 0:
                            target_tx = 'alias(nPercentile(scale(sumSeries(%s),8),95),"tx")' % (','.join(members_octet_tx))
                            target_rx = 'alias(nPercentile(scale(sumSeries(%s),8),95),"rx")' % (','.join(members_octet_rx))
                            params = [
                                ('format', 'json'),
                                ('from' , '%smin' % fromDateMins),
                                ('until', '%smin' % untilDateMins),
                                ('target', target_tx), 
                                ('target', target_rx),
                            ]

                            print("      ---------------------------")

                            # Get 95 percentil for group of members
                            response = getPercentil(session, params)
                            d = response.json()
                            for stat in d['data']:
                                if 'target' not in stat:
                                    continue

                                if 'datapoints' not in stat:
                                    continue

                                data_len = len(stat['datapoints'])
                                if data_len > 0:
                                    val = stat['datapoints'][data_len-1][0]
                                    print("      %s percentil(95): %s" % (stat['target'], format_bandwidth(val)) )
else:
    print("ERROR: unable to get graphboards list: %s" % response.text)

session.close()
