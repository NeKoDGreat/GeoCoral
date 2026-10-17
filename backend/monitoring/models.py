"""
GeoCoral — core data models.

Mirrors the Methodology chapter:
  - Sanctuary: the three selected Samal Island marine sanctuaries
  - CoralRecord: one classification result per submitted photo, GPS-tagged
    (System Architecture: "integration of classification results with
    their corresponding geographic coordinates for geomapping")
  - UserProfile: distinguishes CENRO staff, sanctuary managers, and divers,
    the intended end users named in the Research Locale section
"""

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models


class Sanctuary(models.Model):
    """One of the three selected marine sanctuaries on Samal Island."""

    name = models.CharField(max_length=200, unique=True)
    area_code = models.CharField(
        max_length=20, unique=True,
        help_text="Short site code, e.g. 'ADE-01' — matches area_code in field metadata.csv",
    )
    description = models.TextField(blank=True)

    # Polygon boundary, enables "is this point inside sanctuary X" queries
    # and spatial filtering on the geomapping interface. Optional — can be
    # filled in later via the GIS maintenance site once boundaries are surveyed.
    boundary = gis_models.PolygonField(srid=4326, null=True, blank=True)

    # A representative point (e.g. the sanctuary's main marker/centroid)
    # for map centering when no boundary is available yet.
    center_point = gis_models.PointField(srid=4326, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "sanctuaries"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.area_code})"


class UserProfile(models.Model):
    """Extends Django's built-in User with the application's three roles."""

    ROLE_CHOICES = [
        ("cenro_staff", "CENRO Staff"),
        ("sanctuary_manager", "Sanctuary Manager"),
        ("diver", "Authorized Diver"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="diver")
    assigned_sanctuaries = models.ManyToManyField(
        Sanctuary, blank=True, related_name="managers",
        help_text="Sanctuaries this user is responsible for monitoring.",
    )
    phone_number = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


class CoralRecord(models.Model):
    """One coral photo submission and its classification result.

    Corresponds to the paper's Dataset Description: locally captured
    images are GPS-tagged and plotted on the geomapping interface;
    supplementary (e.g. Kaggle) images used only for model training are
    never represented here, since this table IS the geomapping data.
    """

    LABEL_CHOICES = [
        ("healthy", "Healthy"),
        ("bleached", "Bleached"),
    ]

    image = models.ImageField(upload_to="coral_photos/%Y/%m/")

    # Model output
    predicted_label = models.CharField(max_length=10, choices=LABEL_CHOICES)
    confidence = models.FloatField(
        help_text="Model's confidence in predicted_label, 0.0-1.0"
    )

    # Optional human verification against expert-assessed samples
    # (Validation Against Manually Assessed Coral Samples, in the paper)
    verified_label = models.CharField(
        max_length=10, choices=LABEL_CHOICES, blank=True, null=True,
        help_text="Filled in if an expert manually confirms/corrects the prediction.",
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="verified_records",
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    # Manually tagged species, separate from the verified_by/at pair
    # above since a different expert might tag species than the one
    # who verified health status, at a different time. Not AI-
    # identified — the ResNet50 model only classifies healthy/bleached.
    SPECIES_CHOICES = [
        ("acropora", "Acropora (staghorn/table coral)"),
        ("porites", "Porites (boulder/finger coral)"),
        ("favites", "Favites (brain coral)"),
        ("platygyra", "Platygyra (brain coral)"),
        ("montipora", "Montipora (encrusting/plate coral)"),
        ("pocillopora", "Pocillopora (cauliflower coral)"),
        ("fungia", "Fungia (mushroom coral)"),
        ("diploastrea", "Diploastrea (honeycomb coral)"),
        ("other", "Other"),
        ("unknown", "Unknown / not yet identified"),
    ]
    species = models.CharField(max_length=20, choices=SPECIES_CHOICES, blank=True, null=True)
    species_tagged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="species_tagged_records",
    )
    species_tagged_at = models.DateTimeField(null=True, blank=True)

    # Location — the field this table exists to serve. PointField
    # (longitude, latitude) in WGS84 (SRID 4326), the standard GPS datum.
    location = gis_models.PointField(srid=4326)

    # Field metadata, matching data_prep/prepare_dataset.py's
    # METADATA_COLUMNS and the paper's Dataset Description table.
    captured_at = models.DateTimeField(help_text="Date/time the photo was taken.")
    depth_m = models.FloatField(null=True, blank=True)
    sanctuary = models.ForeignKey(
        Sanctuary, on_delete=models.PROTECT, related_name="coral_records"
    )
    area_code = models.CharField(max_length=20, blank=True)
    photographer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="coral_submissions",
    )

    # GPS source — did the browser/device capture location automatically,
    # or did the submitter enter it manually? (paper: "manual coordinate
    # entry as a fallback")
    gps_source = models.CharField(
        max_length=10,
        choices=[("device", "Device GPS"), ("manual", "Manual Entry")],
        default="device",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-captured_at"]
        indexes = [
            models.Index(fields=["predicted_label"]),
            models.Index(fields=["captured_at"]),
        ]

    def __str__(self):
        return f"{self.get_predicted_label_display()} @ {self.sanctuary.name} ({self.captured_at:%Y-%m-%d})"

    @property
    def effective_label(self):
        """The verified label if an expert has reviewed this record,
        otherwise the model's prediction."""
        return self.verified_label or self.predicted_label
