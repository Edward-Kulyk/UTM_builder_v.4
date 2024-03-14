import json
from collections import defaultdict
import requests

from app import db
from config import Config
from models import UTMLink
from collections import defaultdict
import requests
import time
from config import Config


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
            'authorization': Config.SHORT_IO_API_KEY
        }

        for attempt in range(5):  # Попытаемся до 5 раз при ошибке 429
            response = requests.get(url, headers=headers, params=querystring)
            if response.status_code == 429:
                time.sleep(2 ** attempt)  # Экспоненциальная задержка
            elif response.status_code == 200:
                clicks = response.json().get("humanClicks", 0)
                utm_link.clicks_count = clicks
                db.session.commit()
                break
            else:
                break  # Прерываем цикл при других ошибках


def get_clicks_filter(short_id, startDate, endDate):
    url = f"https://api-v2.short.io/statistics/link/{short_id}"
    querystring = {"period": "custom", "tzOffset": "0", 'startDate': startDate, "endDate": endDate}

    headers = {
        'accept': "*/*",
        'authorization': Config.SHORT_IO_API_KEY
    }

    for attempt in range(5):  # Попытаемся до 5 раз при ошибке 429
        response = requests.get(url, headers=headers, params=querystring)
        if response.status_code == 429:
            time.sleep(2 ** attempt)  # Экспоненциальная задержка
        elif response.status_code == 200:
            clicks = response.json().get("humanClicks", 0)
            return clicks
        else:
            return 0  # Возвращаем 0 при других ошибках


def aggregate_clicks(short_ids, startDate, endDate):
    clicks_aggregated = defaultdict(int)
    clicks_by_short_id = {}
    os_aggregated = defaultdict(int)

    for short_id in short_ids:
        url = f"https://api-v2.short.io/statistics/link/{short_id}"
        querystring = {"period": "custom", "tzOffset": "0", 'startDate': startDate, "endDate": endDate}

        headers = {
            'accept': "*/*",
            'authorization': Config.SHORT_IO_API_KEY
        }

        for attempt in range(5):  # Попытаемся до 5 раз при ошибке 429
            response = requests.get(url, headers=headers, params=querystring)
            if response.status_code == 429:
                time.sleep(2 ** attempt)  # Экспоненциальная задержка
            elif response.status_code == 200:
                data = response.json()
                clicks_by_short_id[short_id] = data.get("humanClicks", 0)
                for entry in data.get("clickStatistics", {}).get("datasets", [])[0].get("data", []):
                    clicks_aggregated[entry["x"][:10]] += int(entry["y"])  # Суммируем клики по датам
                for os_data in data.get('os', []):
                    os_aggregated[os_data['os']] += os_data['score']
                break  # Прерываем цикл после успешного запроса
            else:
                break  # Прерываем цикл при других ошибках

    # Преобразование данных для использования в графике
    os_data_for_chart = [{'os': os, 'score': score} for os, score in os_aggregated.items()]
    clicks_data = [{'x': date, 'y': clicks} for date, clicks in clicks_aggregated.items()]
    return sorted(clicks_data, key=lambda x: x['x']), clicks_by_short_id, os_data_for_chart  # Сортировка данных по дате


def edit_link(id):
    record = UTMLink.query.filter_by(id=id).first()
    url = f"https://api.short.io/links/{record.short_id}"
    payload = json.dumps({
        "allowDuplicates": False,
        "domain": record.domain,
        "path": record.slug,
        "originalURL": f"{record.url}?utm_campaign={record.campaign_name.replace(' ', '+')}&utm_medium={record.campaign_medium.replace(' ', '+')}&utm_source={record.campaign_source.replace(' ', '+')}&utm_content={record.campaign_content.replace(' ', '+')}"
    })
    headers = {
        'accept': "application/json",
        'content-type': "application/json",
        'authorization': Config.SHORT_IO_API_KEY
    }
    response = requests.request("POST", url, data=payload, headers=headers)
    return response


def delete_link(id):
    url = f"https://api.short.io/links/{id}"

    headers = {'authorization': Config.SHORT_IO_API_KEY}

    response = requests.request("DELETE", url, headers=headers)
    return response