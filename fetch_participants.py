'''
This is the script to fetch the participants' name and email addresses from given meeting type (e.g., meeting or webinar)
and meeting ID.

This script is implemented to draw a raffle for a prize and we used this with the online drawing tool:
    https://wheelofnames.com

This generates two intermediate files:
1. fetched_participants_{meeting_type}_{meeting_id}.json
    This contains the raw output from Zoom API call for participants
2. extracted_participants_{meeting_type}_{meeting_id}.tsv
    This contains each participant's name, email address, and partially hidden email address (for privacy issue)
    with the delimiter of a tab character.

And this prints the participants' names and partially hidden email address to console.

This scirpt does not include any participant who does not have name or email address.
When someone rejoined with the same email address multiple times, the first join will be recorded (deduped gby email address)
'''

import datetime
import http.client
import json
import sys
import time

import jwt

if len(sys.argv) != 3 or sys.argv[1] not in {"meeting", "webinar"}:
    raise RuntimeError(
        "Usage: python fetch_participants.py [meeting|webinar] [meeting ID].")

meeting_type = sys.argv[1]
meeting_id = sys.argv[2]

#################
# CONFIGURATION #
#################

# JWT API Key, API Secret
API_KEY = "YOUR_API_KEY"
API_SEC = "YOUR_API_SECRET"


def fetch_one_page(meeting_type, meeting_id, next_page_token=None):
    payload = {
        "iss": API_KEY,
        "exp": (datetime.datetime.now() + datetime.timedelta(seconds=30)).timestamp()
    }

    jwt_encoded = str(jwt.encode(payload, API_SEC), "utf-8")

    conn = http.client.HTTPSConnection("api.zoom.us")
    headers = {
        "authorization": "Bearer %s" % jwt_encoded,
        "content-type": "application/json"
    }

    api_endpoint = f"/v2/metrics/{meeting_type}s/{meeting_id}/participants?page_size=10&type=past"
    if meeting_type == "webinar":
        api_endpoint += "&include_fields=registrant_id"
    if next_page_token:
        api_endpoint += f"&next_page_token={next_page_token}"

    conn.request("GET", api_endpoint, headers=headers)
    res = conn.getresponse()
    response_string = res.read().decode("utf-8")
    response_obj = json.loads(response_string)

    return response_obj


# Fetch the return of Zoom participant API call
result_file = f"fetched_participants_{meeting_type}_{meeting_id}.json"
with open(result_file, "w") as outfile:
    next_page_token = None
    while True:
        response_obj = fetch_one_page(
            meeting_type, meeting_id, next_page_token)
        outfile.write(f"{json.dumps(response_obj)}\n")
        next_page_token = response_obj.get("next_page_token", None)
        if not next_page_token:
            break
        time.sleep(0.5)

# Extract participant's name and email address
participants = {}
with open(result_file) as infile:
    for line in infile:
        j_obj = json.loads(line)
        for p in j_obj["participants"]:
            email = p.get("email")
            if not email or email in participants:
                continue
            name = p.get("user_name")
            if not name:
                continue
            participants[email] = name

# Write the name, email address, and partically hidden email address into TSV file
# Also print to console the name and partically hidden email address
with open(f"extracted_participants_{meeting_type}_{meeting_id}.tsv", "w") as outfile:
    for email, name in participants.items():
        signature = email.split("@")[0][:4] + "*"
        outfile.write(f"{name}\t{email}\t{name} ({signature})\n")
        print(f"{name} ({signature})")
