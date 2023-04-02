from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from incidents.models import Report, Incident
from incidents.sources.tflapiv1 import check as check_tflv1
from incidents.sources.tflapiv2 import check as check_tflv2


def consolidate_incidents():
    # Take all the reports and consolidate them into incidents
    for report in Report.objects.filter(resolved=False):
        # Check if there is an incident for this station
        incident = Incident.objects.filter(station=report.station).first()

        if incident is None:
            # Create a new incident
            incident = Incident(
                information=report.information,
                station=report.station,
                text=report.text,
                start_time=report.start_time,
                end_time=report.end_time,
                resolved=report.resolved,
            )
            incident.save()
        else:
            # Update the existing incident
            incident.information = report.information
            incident.text = report.text
            incident.start_time = report.start_time
            incident.end_time = report.end_time
            incident.resolved = report.resolved
            incident.save()

        # Add the report to the incident
        incident.reports.add(report)

    for incident in Incident.objects.all():
        # Check if the incident has been resolved
        if incident.reports.filter(resolved=False).count() == 0:
            incident.resolved = True
            incident.end_time = timezone.now()
            incident.save()


class Command(BaseCommand):
    help = "Updates the incidents list"

    def handle(self, *args, **options):
        try:
            check_tflv1()
            check_tflv2()
            consolidate_incidents()
        except Exception as e:
            raise CommandError(f"Error updating incidents list: {e}")

        self.stdout.write(self.style.SUCCESS("Successfully updated incident list"))
