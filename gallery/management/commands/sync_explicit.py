from django.core.management.base import BaseCommand
from django.conf import settings
import json
from gallery.utils import sync_data_with_json
BASE_DIR = settings.BASE_DIR

class Command(BaseCommand):
    help = 'Synchronize the gallery with the database'

    def handle(self, *args, **kwargs):
        # This is a placeholder for the actual synchronization logic
        # For example, you might want to check for new images, update existing ones, etc.
        self.stdout.write(self.style.SUCCESS('Synchronization complete.'))
        with open(f'{BASE_DIR}/subs.json', 'r') as file:
            subs = json.loads(file.read())
        if subs["subs"]:
            self.stdout.write(self.style.SUCCESS(f'Found {len(subs["subs"])} subreddits to process.'))
        sync_data_with_json(subs["subs"])
