from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import CoralRecord, Sanctuary, UserProfile


@admin.register(Sanctuary)
class SanctuaryAdmin(GISModelAdmin):
    list_display = ["name", "area_code"]
    search_fields = ["name", "area_code"]


@admin.register(CoralRecord)
class CoralRecordAdmin(GISModelAdmin):
    list_display = [
        "id", "predicted_label", "confidence", "verified_label",
        "sanctuary", "captured_at", "photographer",
    ]
    list_filter = ["predicted_label", "verified_label", "sanctuary", "gps_source"]
    search_fields = ["area_code"]
    autocomplete_fields = ["sanctuary", "photographer", "verified_by"]
    readonly_fields = ["predicted_label", "confidence", "created_at"]


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "role", "phone_number"]
    list_filter = ["role"]
    autocomplete_fields = ["user"]
