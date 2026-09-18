"""
Seeds placeholder Sanctuary records so the app has something to point
at immediately. Edit the SANCTUARIES list below with your actual three
selected Samal Island sanctuaries (names, area codes, real coordinates)
once you have them — these are placeholders based on the area codes
used in the ML project's example metadata.

Run:
    python manage.py seed_sanctuaries
"""

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand

from monitoring.models import Sanctuary

SANCTUARIES = [
    {
        "name": "Adecor Marine Sanctuary",
        "area_code": "ADE-01",
        "center_point": Point(125.6836, 7.0731, srid=4326),
        "description": "Placeholder — replace with real boundary/description.",
    },
    {
        "name": "Talikud Marine Sanctuary",
        "area_code": "TAL-01",
        "center_point": Point(125.6420, 7.0295, srid=4326),
        "description": "Placeholder — replace with real boundary/description.",
    },
    {
        "name": "Kaputian Marine Sanctuary",
        "area_code": "KAP-01",
        "center_point": Point(125.7025, 6.9765, srid=4326),
        "description": "Placeholder — replace with real boundary/description.",
    },
]


class Command(BaseCommand):
    help = "Seeds the three Samal Island marine sanctuaries (placeholder data — edit before real use)."

    def handle(self, *args, **options):
        created_count = 0
        for entry in SANCTUARIES:
            sanctuary, created = Sanctuary.objects.get_or_create(
                area_code=entry["area_code"],
                defaults={
                    "name": entry["name"],
                    "center_point": entry["center_point"],
                    "description": entry["description"],
                },
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created: {sanctuary}"))
            else:
                self.stdout.write(f"Already exists: {sanctuary}")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. {created_count} new sanctuary record(s) created."
        ))
        self.stdout.write(
            "Edit monitoring/management/commands/seed_sanctuaries.py with your "
            "real sanctuary names, coordinates, and boundaries when available."
        )
