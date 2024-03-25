import datetime
from datetime import datetime
from functools import wraps
from io import BytesIO
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from flask import jsonify, send_file
from flask import (request, render_template, redirect, Blueprint)
from sqlalchemy import func, Integer, desc, cast
from sqlalchemy.orm import aliased
from itertools import chain
from app import db
from models.models import UTMLink, ExcludedOption, Campaign
from utils.db_utils import extract_first_if_tuple
from utils.short_link import update_clicks_count, create_short_link, aggregate_clicks, edit_link, \
    delete_link


main = Blueprint('main', __name__, )


@main.route('/', methods=['GET', 'POST'])
def index():
    short_secure_url = None
    utm_entries = UTMLink.query.all()
    error_message = None

    excluded_campaign_sources = [option[0] for option in ExcludedOption.query.filter(
        ExcludedOption.option_type == 'campaign_sources[]').with_entities(ExcludedOption.option_value).distinct().all()]

    excluded_campaign_mediums = [option[0] for option in ExcludedOption.query.filter(
        ExcludedOption.option_type == 'campaign_mediums[]').with_entities(ExcludedOption.option_value).distinct().all()]

    excluded_campaign_names = [option[0] for option in ExcludedOption.query.filter(
        ExcludedOption.option_type == 'campaign_names[]').with_entities(
        ExcludedOption.option_value).distinct().all()]

    excluded_campaign_contents = [option[0] for option in ExcludedOption.query.filter(
        ExcludedOption.option_type == 'campaign_contents[]').with_entities(
        ExcludedOption.option_value).distinct().all()]

    excluded_urls = [option[0] for option in ExcludedOption.query.filter(
        ExcludedOption.option_type == 'urls[]').with_entities(ExcludedOption.option_value).distinct().all()]

    excluded_campaign_sources = extract_first_if_tuple(excluded_campaign_sources)
    excluded_campaign_mediums = extract_first_if_tuple(excluded_campaign_mediums)
    excluded_campaign_contents = extract_first_if_tuple(excluded_campaign_contents)
    excluded_urls = extract_first_if_tuple(excluded_urls)

    if request.method == 'POST':
        url = request.form['url']
        campaign_content = request.form.get('campaign_content', ' ')
        campaign_source = request.form['campaign_source']
        campaign_medium = request.form['campaign_medium']
        campaign_name = request.form['campaign_name']
        domain = request.form['domain']
        slug = request.form.get('slug', "")

        if url == 'other':
            url = request.form['url_other']
        if campaign_content == 'other':
            campaign_content = request.form['campaign_content_other']
        if campaign_source == 'other':
            campaign_source = request.form['campaign_source_other']
        if campaign_medium == 'other':
            campaign_medium = request.form['campaign_medium_other']
        if campaign_name == 'other':
            campaign_name = request.form['campaign_name_other']

        # Construct the UTM link with spaces replaced by '+'
        utm_link = f"{url}?utm_campaign={campaign_name.replace(' ', '+')}&utm_medium={campaign_medium.replace(' ', '+')}&utm_source={campaign_source.replace(' ', '+')}&utm_content={campaign_content.replace(' ', '+')}"

        # Check if a similar record already exists
        existing_record = UTMLink.query.filter_by(
            url=url,
            campaign_content=campaign_content,
            campaign_source=campaign_source,
            campaign_medium=campaign_medium,
            campaign_name=campaign_name,
            domain=domain,
            slug=slug,
        ).first()

        if existing_record:
            error_message = "Similar record already exists."
        else:

            # Create UTM link using Short.io API
            short_url = create_short_link(domain, slug, utm_link)

            if short_url.get('error'):
                # Handle error case (e.g., log the error, display an error message)
                error_message = short_url['error']

            else:
                # Update the database with short link information
                short_id = short_url['idString']
                short_secure_url = short_url['secureShortURL']
                if slug == "":
                    slug = short_url['path']
                # Save data to the database
                utm_link = UTMLink(
                    url=url, campaign_content=campaign_content, campaign_source=campaign_source,
                    campaign_medium=campaign_medium, campaign_name=campaign_name,
                    domain=domain, slug=slug, short_id=short_id, short_secure_url=short_secure_url
                )

                db.session.add(utm_link)
                db.session.commit()

    # Fetch unique values for dropdowns
    unique_campaign_sources = [source[0] for source in UTMLink.query.with_entities(UTMLink.campaign_source)
    .filter(UTMLink.campaign_source.notin_(excluded_campaign_sources)).distinct().all()]

    unique_campaign_mediums = [medium[0] for medium in UTMLink.query.with_entities(UTMLink.campaign_medium)
    .filter(UTMLink.campaign_medium.notin_(excluded_campaign_mediums)).distinct().all()]

    unique_campaign_contents = [content[0] for content in UTMLink.query.with_entities(UTMLink.campaign_content)
    .filter(UTMLink.campaign_content.notin_(excluded_campaign_contents)).distinct().all()]

    unique_campaign_names = [name[0] for name in Campaign.query.with_entities(Campaign.name)
    .filter(Campaign.name.notin_(excluded_campaign_names)).distinct().all()]

    unique_urls = list(set(chain(
        [url[0] for url in
         UTMLink.query.with_entities(UTMLink.url).filter(UTMLink.url.notin_(excluded_urls)).distinct().all()],
        [url[0] for url in
         Campaign.query.with_entities(Campaign.url_by_default).filter(
             Campaign.url_by_default.notin_(excluded_urls)).distinct().all()]
    )))

    if short_secure_url is None:
        return render_template('index.html', utm_entries=utm_entries, unique_campaign_contents=unique_campaign_contents,
                               unique_campaign_sources=unique_campaign_sources,
                               unique_campaign_mediums=unique_campaign_mediums,
                               unique_campaign_names=unique_campaign_names,
                               unique_url=unique_urls, error_message=error_message)
    else:
        return render_template('index.html', utm_entries=utm_entries, unique_campaign_contents=unique_campaign_contents,
                               unique_campaign_sources=unique_campaign_sources,
                               unique_campaign_mediums=unique_campaign_mediums,
                               unique_campaign_names=unique_campaign_names,
                               unique_url=unique_urls, short_url=short_secure_url, error_message=error_message)


@main.route('/exclude-options', methods=['GET', 'POST'])
def exclude_options():
    if request.method == 'POST':
        for field_name, values in request.form.lists():
            if field_name.startswith('exclude_'):
                option_type = field_name.replace('exclude_', '')
                for value in values:
                    excluded_option = ExcludedOption(option_type=option_type, option_value=value)
                    db.session.add(excluded_option)

        db.session.commit()

    excluded_campaign_sources = [option[0] for option in ExcludedOption.query.filter(
        ExcludedOption.option_type == 'campaign_sources[]').with_entities(ExcludedOption.option_value).distinct().all()]
    excluded_campaign_mediums = [option[0] for option in ExcludedOption.query.filter(
        ExcludedOption.option_type == 'campaign_mediums[]').with_entities(ExcludedOption.option_value).distinct().all()]

    excluded_campaign_contents = [option[0] for option in ExcludedOption.query.filter(
        ExcludedOption.option_type == 'campaign_contents[]').with_entities(
        ExcludedOption.option_value).distinct().all()]

    excluded_campaign_names = [option[0] for option in ExcludedOption.query.filter(
        ExcludedOption.option_type == 'campaign_names[]').with_entities(
        ExcludedOption.option_value).distinct().all()]

    excluded_urls = [option[0] for option in ExcludedOption.query.filter(
        ExcludedOption.option_type == 'urls[]').with_entities(ExcludedOption.option_value).distinct().all()]

    excluded_campaign_sources = extract_first_if_tuple(excluded_campaign_sources)
    excluded_campaign_mediums = extract_first_if_tuple(excluded_campaign_mediums)
    excluded_campaign_contents = extract_first_if_tuple(excluded_campaign_contents)
    excluded_campaign_names = extract_first_if_tuple(excluded_campaign_names)
    excluded_urls = extract_first_if_tuple(excluded_urls)

    unique_campaign_sources = [source[0] for source in UTMLink.query.with_entities(UTMLink.campaign_source)
    .filter(UTMLink.campaign_source.notin_(excluded_campaign_sources)).distinct().all()]

    unique_campaign_mediums = [medium[0] for medium in UTMLink.query.with_entities(UTMLink.campaign_medium)
    .filter(UTMLink.campaign_medium.notin_(excluded_campaign_mediums)).distinct().all()]

    unique_campaign_contents = [content[0] for content in UTMLink.query.with_entities(UTMLink.campaign_content)
    .filter(UTMLink.campaign_content.notin_(excluded_campaign_contents)).distinct().all()]

    unique_campaign_names = [name[0] for name in Campaign.query.with_entities(Campaign.name)
    .filter(Campaign.name.notin_(excluded_campaign_names)).distinct().all()]

    unique_urls = [url[0] for url in UTMLink.query.with_entities(UTMLink.url)
    .filter(UTMLink.url.notin_(excluded_urls)).distinct().all()]

    return render_template('exclude_options.html',
                           unique_campaign_contents=unique_campaign_contents,
                           unique_campaign_sources=unique_campaign_sources,
                           unique_campaign_mediums=unique_campaign_mediums,
                           unique_campaign_names=unique_campaign_names,
                           unique_urls=unique_urls)


@main.route('/manage-exclusions', methods=['GET', 'POST'])
def manage_exclusions():
    if request.method == 'POST':
        for field_name in request.form:
            if field_name.startswith('include_'):
                option_type = field_name.replace('include_', '')
                included_values = request.form.getlist(field_name)
                for value in included_values:
                    ExcludedOption.query.filter_by(option_type=option_type, option_value=value).delete()
        db.session.commit()
    excluded_campaign_sources = ExcludedOption.query.filter(
        ExcludedOption.option_type == 'campaign_sources[]').distinct().all()
    excluded_campaign_mediums = ExcludedOption.query.filter(
        ExcludedOption.option_type == 'campaign_mediums[]').distinct().all()
    excluded_campaign_contents = ExcludedOption.query.filter(
        ExcludedOption.option_type == 'campaign_contents[]').distinct().all()
    excluded_campaign_names = ExcludedOption.query.filter(
        ExcludedOption.option_type == 'campaign_names[]').distinct().all()
    excluded_urls = ExcludedOption.query.filter(ExcludedOption.option_type == 'urls[]').distinct().all()

    return render_template('manage_exclusions.html',
                           excluded_campaign_contents=excluded_campaign_contents,
                           excluded_campaign_sources=excluded_campaign_sources,
                           excluded_campaign_mediums=excluded_campaign_mediums,
                           excluded_campaign_names=excluded_campaign_names,
                           excluded_urls=excluded_urls)


@main.route('/campaigns', methods=['GET'])
def campaigns():
    utm_link = aliased(UTMLink)
    campaign = aliased(Campaign)

    # Получаем все записи, группируем их по названию кампании
    grouped_campaigns = db.session.query(
        utm_link.campaign_name,
        func.group_concat(utm_link.campaign_content).label('campaign_contents'),
        func.group_concat(utm_link.campaign_source).label('campaign_sources'),
        func.group_concat(utm_link.campaign_medium).label('campaign_mediums'),
        func.group_concat(utm_link.domain).label('domains'),
        func.group_concat(utm_link.slug).label('slugs'),
        func.group_concat(utm_link.short_id).label('short_ids'),
        func.group_concat(utm_link.short_secure_url).label('short_secure_urls'),
        campaign.start_date.label('start_date'),
        # Агрегированные строки значений кликов
        func.group_concat(utm_link.clicks_count).label('clicks_counts'),
        func.group_concat(utm_link.clicks_count24h).label('clicks_counts_24h'),
        func.group_concat(utm_link.clicks_count1w).label('clicks_counts_1w'),
        func.group_concat(utm_link.clicks_count2w).label('clicks_counts_2w'),
        func.group_concat(utm_link.clicks_count3w).label('clicks_counts_3w'),
        # Суммарные значения кликов за разные периоды
        func.sum(cast(utm_link.clicks_count, Integer)).label('total_clicks'),
        func.sum(cast(utm_link.clicks_count24h, Integer)).label('total_clicks_24h'),
        func.sum(cast(utm_link.clicks_count1w, Integer)).label('total_clicks_1w'),
        func.sum(cast(utm_link.clicks_count2w, Integer)).label('total_clicks_2w'),
        func.sum(cast(utm_link.clicks_count3w, Integer)).label('total_clicks_3w')
    ).join(campaign).filter(campaign.hide != True).group_by(utm_link.campaign_name).order_by(desc(utm_link.id)).all()

    return render_template('campaigns.html', grouped_campaigns=grouped_campaigns)


@main.route('/import', methods=['GET'])
def import_excel_data():
    # Read Excel file into a pandas DataFrame
    df = pd.read_excel("Link.xlsx")

    # Iterate through DataFrame rows and add to the database
    for index, row in df.iterrows():
        utm_link = UTMLink(
            url=row['url'],
            campaign_content=row['campaign_content'],
            campaign_source=row['campaign_source'],
            campaign_medium=row['campaign_medium'],
            campaign_name=row['campaign_name'],
            domain=row['domain'],
            slug=row['slug'],
            short_id=row['short_id'],
            short_secure_url=row['short_secure_url'],
            clicks_count=row["clicks_count"],
            clicks_count24h=row["clicks_count24h"],
            clicks_count1w=row["clicks_count1w"],
            clicks_count2w=row["clicks_count2w"],
            clicks_count3w=row["clicks_count3w"]
        )
        db.session.add(utm_link)

    # Commit changes to the database
    db.session.commit()
    return "Import success"


@main.route('/filter_setting', methods=['GET', 'POST'])
def filter_setting():
    if request.method == 'POST':
        # Используйте .getlist() вместо .get() для получения всех выбранных значений
        urls = request.form.getlist('url')
        campaign_sources = request.form.getlist('campaign_source')
        campaign_mediums = request.form.getlist('campaign_medium')
        campaign_names = request.form.getlist('campaign_name')
        campaign_contents = request.form.getlist('campaign_content')
        date_from = request.form.get('date_from')
        date_to = request.form.get('date_to')

        # Начинаем с базового запроса
        query = UTMLink.query

        # Применяем фильтры только для заполненных полей
        if urls:
            query = query.filter(UTMLink.url.in_(urls))
        if campaign_sources:
            query = query.filter(UTMLink.campaign_source.in_(campaign_sources))
        if campaign_mediums:
            query = query.filter(UTMLink.campaign_medium.in_(campaign_mediums))
        if campaign_names:
            query = query.filter(UTMLink.campaign_name.in_(campaign_names))
        if campaign_contents:
            query = query.filter(UTMLink.campaign_content.in_(campaign_contents))

        # Выполняем запрос
        results = query.all()
        short_ids = [result.short_id for result in results]
        clicks_data, clicks_by_line, os_data_for_chart = aggregate_clicks(short_ids, date_from, date_to)

        for result in results:
            result.clicks = clicks_by_line.get(result.short_id, 0)

        total_clicks = sum(clicks_by_line.values())
        # Render the results page, passing in the results and total clicks
        return render_template('filtered_utm.html', results=results, total_clicks=total_clicks, clicks_data=clicks_data,
                               os_data=os_data_for_chart)

    if request.method == "GET":
        # Query to get all unique campaign contents
        unique_campaign_contents = UTMLink.query.with_entities(UTMLink.campaign_content).distinct().all()

        # Query to get all unique campaign sources
        unique_campaign_sources = UTMLink.query.with_entities(UTMLink.campaign_source).distinct().all()

        # Query to get all unique campaign mediums
        unique_campaign_mediums = UTMLink.query.with_entities(UTMLink.campaign_medium).distinct().all()

        # Query to get all unique campaign names
        unique_campaign_names = UTMLink.query.with_entities(UTMLink.campaign_name).distinct().all()

        # Query to get all unique URLs
        unique_urls = UTMLink.query.with_entities(UTMLink.url).distinct().all()

        return render_template('filter_setting.html', unique_campaign_contents=unique_campaign_contents,
                               unique_campaign_sources=unique_campaign_sources,
                               unique_campaign_mediums=unique_campaign_mediums,
                               unique_campaign_names=unique_campaign_names,
                               unique_url=unique_urls)


@main.route('/update-clicks', methods=['GET'])
def update_clicks():
    update_clicks_count()
    return redirect("/campaigns")


@main.route('/edit-row/<string:id>', methods=['POST'])
def edit_record(id):
    data = request.json
    record = UTMLink.query.filter_by(short_id=str(id)).first()
    if record:
        record.campaign_source = data['campaign_source']
        record.campaign_medium = data['campaign_medium']
        record.campaign_content = data.get('campaign_content')  # Используйте .get для необязательных полей
        db.session.commit()
        edit_link(record.id)
        return jsonify({'status': 'success', 'message': 'Record updated successfully'})
    else:
        return jsonify({'status': 'error', 'message': 'Record not found'})


@main.route('/delete-row/<string:id>', methods=['POST'])
def delete_record(id):
    record = UTMLink.query.filter_by(short_id=str(id)).first()
    if record:
        delete_link(record.short_id)
        db.session.delete(record)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Record deleted successfully'})
    else:
        return jsonify({'status': 'error', 'message': 'Record not found'})


@main.route('/data-stamp', methods=['GET'])
def data_stamp():
    return render_template("data-stamp.html")


@main.route('/add_data_stamp', methods=['POST'])
def add_data_stamp():
    photo = request.files['photo']
    date_str = request.form['date']
    date = datetime.datetime.strptime(date_str, '%Y-%m-%d')

    img = Image.open(photo.stream)
    if img.mode != 'RGB':
        img = img.convert('RGB')

    draw = ImageDraw.Draw(img)

    # Using a relative font size based on the image height, ensuring it's readable
    relative_font_size = int(min(img.size) / 20)
    font_path = "arial.ttf"  # Make sure this path is correct for your setup
    font = ImageFont.truetype(font_path, relative_font_size)

    text = date.strftime('%Y-%m-%d')
    text_color = (255, 255, 255)  # White

    # Adjust text positioning a bit higher and to the right
    x_adjust = 40  # Increase for further right
    y_adjust = 20  # Increase for higher
    x = img.width - (relative_font_size * len(text) // 2) - x_adjust
    y = img.height - (relative_font_size * 2) - y_adjust

    # Adding a simple shadow for legibility
    draw.text((x + 1, y + 1), text, font=font, fill=(0, 0, 0))  # Black shadow
    draw.text((x, y), text, font=font, fill=text_color)

    img_bytes = BytesIO()
    img.save(img_bytes, 'JPEG')  # Ensure to save as RGB for JPEG
    img_bytes.seek(0)

    return send_file(img_bytes, mimetype='image/jpeg', as_attachment=True, download_name='modified_image.jpg')


@main.route('/add_campaign', methods=['GET', 'POST'])
def add_campaign():
    if request.method == 'POST':
        name = request.form['name']
        url_by_default = request.form['url_by_default']
        domain_by_default = request.form['domain_by_default']
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()

        # Validate start_date
        if not start_date:
            # Provide a default value or handle empty start_date based on your requirements
            start_date = datetime.date.today()  # Example: Use today's date as default

        campaign = Campaign(
            name=name,
            url_by_default=url_by_default,
            domain_by_default=domain_by_default,
            start_date=start_date,
            hide=False  # Assuming hide is a boolean field
        )

        db.session.add(campaign)
        db.session.commit()

        return render_template("campaign_creation.html")

    return render_template('campaign_creation.html')


@main.route('/get_default_values', methods=['POST'])
def get_default_values():
    campaign_name = request.json['campaign_name']
    default_values = Campaign.query.filter_by(name=campaign_name).first()
    print(campaign_name)
    return jsonify({
        'url_by_default': default_values.url_by_default,
        'domain_by_default': default_values.domain_by_default
    })


@main.route('/edit_campaing_name_list', methods=['GET'])
def edit_campaing_name_list():
    campaigns = Campaign.query.all()
    return render_template('campaign_name_list.html', campaigns=campaigns)


@main.route('/edit-campaign-row/<int:id>', methods=['POST'])
def edit_row(id):
    # Получаем данные из запроса
    data = request.json
    start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d').date()
    data['hide'] = False if data['hide'].lower() == 'false' else True
    # Находим запись в базе данных по переданному id
    campaign = Campaign.query.get(id)

    # Обновляем данные кампании
    campaign.name = data['name']
    campaign.url_by_default = data['url_by_default']
    campaign.domain_by_default = data['domain_by_default']
    campaign.start_date = start_date
    campaign.hide = data['hide']

    # Сохраняем изменения
    db.session.commit()

    # Отправляем ответ клиенту
    return jsonify({'status': 'success', 'message': 'Row updated successfully'})
