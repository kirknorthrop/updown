from django.core.management.base import BaseCommand, CommandError

from stations.utils import update_station_list


class Command(BaseCommand):
    help = "Updates the stations list"

    def handle(self, *args, **options):
        try:
            update_station_list()
        except Exception:
            raise CommandError("Error updating station list")

        self.stdout.write(self.style.SUCCESS("Successfully updated station list"))
