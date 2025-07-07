from django.management.base import BaseCommand
from gallery.models import *
from django.conf import settings
import json

BASE_DIR = settings.BASE_DIR

class Command(BaseCommand):
    help = 'Synchronize the gallery with the database'

    def handle(self, *args, **kwargs):
        # This is a placeholder for the actual synchronization logic
        # For example, you might want to check for new images, update existing ones, etc.
        self.stdout.write(self.style.SUCCESS('Synchronization complete.'))
        with open(f'{BASE_DIR}/subs.json', 'r') as file:
            subs = json.loads(file.read())
        for sub in subs:
            subrd = SubReddit.objects.get_or_create(
                name=sub,
                defaults={
                    'direct_url': f'https://www.reddit.com/r/{sub}/',
                    'sub_reddit': f'r/{sub}'
                }
            )

        for image in images:
            self.stdout.write(f'Image ID: {image.id}, Title: {image.title}')
