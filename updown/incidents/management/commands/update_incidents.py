from django.core.management.base import BaseCommand, CommandError

from incidents.sources.tflapiv1 import check as check_tflv1
from incidents.sources.tflapiv2 import check as check_tflv2


class Command(BaseCommand):
    help = "Updates the incidents list"

    def handle(self, *args, **options):
        try:
            check_tflv1()
            check_tflv2()
        except Exception as e:
            raise CommandError(f"Error updating incidents list: {e}")

        self.stdout.write(self.style.SUCCESS("Successfully updated incident list"))
