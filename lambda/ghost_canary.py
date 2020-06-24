import json
from botocore.vendored import requests
import os

def handler(event, context):
    print('request: {}'.format(json.dumps(event)))
    website_url = os.environ['WebsiteUrl']

    # Very simple check. Just see if the website is up.
    response = requests.get(website_url)
    if response.status_code != 200:
        raise Exception("Website is unavailble. Got status code %i" % response.status_code)