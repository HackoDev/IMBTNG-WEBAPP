import uuid

import requests
from celery import shared_task
from django.utils.text import slugify

from apps.core.parser import FootballDataFeed
from apps.core.models import EventCategory, Event, Team


@shared_task()
def data_feeds_loader():
    data_feeds_parsers = [
        FootballDataFeed()
    ]
    for parser in data_feeds_parsers:
        for item in parser.fetch_page():
            event_name = slugify(''.join(
                [item['name'], str(item['starts_at'])]
            ))
            category, _ = EventCategory.objects.get_or_create(
                name=item['category'])
            obj, _ = Event.objects.get_or_create(
                name=item['name'],
                starts_at=item['starts_at'],
                defaults={
                    'category_id': category.id,
                    'name': item['name'],
                    'slug': event_name,
                })
            for team_data in item['teams']:
                team, _ = Team.objects.get_or_create(
                    name=team_data['name'],
                    slug=slugify('-'.join(
                        [team_data['name'], str(obj.category_id)]
                    ))
                )
                obj.teams.add(team)


@shared_task()
def upload_event_file_from_server(event_id):
    event = Event.objects.get(pk=event_id)
    remote_image_url = event.logo_url
    r = requests.get(remote_image_url, stream=True)
    if r.status_code == 200:
        file_name = 'uploads/{uuid}.{ext}'.format(
            ext=remote_image_url.rpartition('.')[2], uuid=str(uuid.uuid4()))
        r.raw.decode_content = True
        event.logo.save(file_name, r.raw)
