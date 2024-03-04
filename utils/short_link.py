import json

import requests

from app import db
from config import Config
from models import UTMLink


def create_short_link(domain, slug, long_url):
    api_url = 'https://api.short.io/links'
    headers = {
        'Content-Type': 'application/json',
        'authorization': Config.SHORT_IO_API_KEY,
    }
    if slug == "":
        data = {
            'originalURL': long_url,
            'domain': domain,
            "title": "ACCZ | API Created"
        }
    else:
        data = {
            'originalURL': long_url,
            'domain': domain,
            'path': slug,
            "title": "ACCZ | API Created"
        }

    response = requests.post(api_url, headers=headers, data=json.dumps(data))
    print(long_url)
    return response.json()


def update_clicks_count():
    utm_links = UTMLink.query.all()

    for utm_link in utm_links:
        url = f"https://api-v2.short.io/statistics/link/{utm_link.short_id}"
        querystring = {"period": "total", "tzOffset": "0"}

        headers = {
            'accept': "*/*",
            'authorization': 'sk_BNIl8NH1FEMMaVxF'
        }

        response = requests.get(url, headers=headers, params=querystring)

        if response.status_code == 200:
            clicks = response.json().get("humanClicks", 0)
            utm_link.clicks_count = clicks
            db.session.commit()

def get_clicks_filter(short_id,startDate,endDate):
    url = f"https://api-v2.short.io/statistics/link/{short_id}"
    querystring = {"period": "custom", "tzOffset": "0", 'startDate': startDate, "endDate": endDate}

    headers = {
        'accept': "*/*",
        'authorization': 'sk_BNIl8NH1FEMMaVxF'
    }

    response = requests.get(url, headers=headers, params=querystring)
    if response.status_code == 200:
        clicks = response.json().get("humanClicks", 0)
        return clicks
    else:
        return 0
