import json
from collections import defaultdict
import requests
from datetime import datetime, timedelta
from sqlalchemy.orm import joinedload
from app import db
from config import Config
from models import UTMLink, Campaign
from collections import defaultdict
import requests
import time


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
    # Получаем ссылки и связанные кампании
    utm_links = UTMLink.query. \
        join(Campaign, UTMLink.campaign_name == Campaign.name). \
        filter(Campaign.hide == False).all()

    current_date = datetime.utcnow().date()

    for utm_link in utm_links:
        campaign_start_date = utm_link.campaign.start_date

        # Определяем конечные даты для каждого периода
        end_date_24h = campaign_start_date + timedelta(days=1)
        end_date_1w = campaign_start_date + timedelta(weeks=1)
        end_date_2w = campaign_start_date + timedelta(weeks=2)
        end_date_3w = campaign_start_date + timedelta(weeks=3)

        # Общее количество кликов с начала кампании до текущего момента
        utm_link.clicks_count = get_clicks_total(utm_link.short_id)

        # Клики за первые сутки
        if current_date >= end_date_24h:
            utm_link.clicks_count24h = get_clicks_filter(utm_link.short_id, campaign_start_date, end_date_24h)

        # Клики за первую неделю
        if current_date >= end_date_1w:
            utm_link.clicks_count1w = get_clicks_filter(utm_link.short_id, campaign_start_date, end_date_1w)

        # Клики за вторую неделю
        if current_date >= end_date_2w:
            utm_link.clicks_count2w = get_clicks_filter(utm_link.short_id, campaign_start_date, end_date_2w)

        # Клики за третью неделю
        if current_date >= end_date_3w:
            utm_link.clicks_count3w = get_clicks_filter(utm_link.short_id, campaign_start_date, end_date_3w)

        # Сохраняем изменения в базе данных
        db.session.commit()


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

def get_clicks_total(short_id):
    url = f"https://api-v2.short.io/statistics/link/{short_id}"
    querystring = {"period": "total", "tzOffset": "0",}

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