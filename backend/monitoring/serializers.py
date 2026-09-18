from django.contrib.gis.geos import Point
from rest_framework import serializers

from .models import CoralRecord, Sanctuary


class SanctuarySerializer(serializers.ModelSerializer):
    center_latitude = serializers.SerializerMethodField()
    center_longitude = serializers.SerializerMethodField()

    class Meta:
        model = Sanctuary
        fields = [
            "id", "name", "area_code", "description",
            "center_latitude", "center_longitude",
        ]

    def get_center_latitude(self, obj):
        return obj.center_point.y if obj.center_point else None

    def get_center_longitude(self, obj):
        return obj.center_point.x if obj.center_point else None


class CoralRecordSerializer(serializers.ModelSerializer):
    """Read serializer — flattens the PointField into plain lat/lon for
    the Leaflet.js frontend, and exposes the sanctuary name directly."""

    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    sanctuary_name = serializers.CharField(source="sanctuary.name", read_only=True)
    effective_label = serializers.CharField(read_only=True)

    class Meta:
        model = CoralRecord
        fields = [
            "id", "image", "predicted_label", "confidence",
            "verified_label", "effective_label",
            "latitude", "longitude", "captured_at", "depth_m",
            "sanctuary", "sanctuary_name", "area_code",
            "gps_source", "created_at",
        ]
        read_only_fields = ["predicted_label", "confidence", "created_at"]

    def get_latitude(self, obj):
        return obj.location.y

    def get_longitude(self, obj):
        return obj.location.x


class CoralRecordUploadSerializer(serializers.ModelSerializer):
    """Write serializer for the image submission endpoint. Accepts plain
    latitude/longitude (matching what a browser's Geolocation API or a
    manual-entry fallback form would send) and builds the PointField
    internally — the client never needs to construct GIS geometry."""

    latitude = serializers.FloatField(write_only=True)
    longitude = serializers.FloatField(write_only=True)

    class Meta:
        model = CoralRecord
        fields = [
            "image", "latitude", "longitude", "captured_at", "depth_m",
            "sanctuary", "area_code", "gps_source",
        ]

    def validate_latitude(self, value):
        if not -90 <= value <= 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value):
        if not -180 <= value <= 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value

    def create(self, validated_data):
        lat = validated_data.pop("latitude")
        lon = validated_data.pop("longitude")
        validated_data["location"] = Point(lon, lat, srid=4326)  # GEOS Point is (x=lon, y=lat)
        return super().create(validated_data)
