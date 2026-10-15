"""
GeoCoral — API views.

CoralRecordViewSet.create() is the "image submission" endpoint from the
paper's System Architecture: a photo + GPS + field metadata comes in,
the trained ResNet50 model classifies it, and the result is stored
GPS-tagged for the geomapping interface to read.
"""

from django.utils.dateparse import parse_datetime
from rest_framework import permissions, status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from . import ml_service
from .models import CoralRecord, Sanctuary
from .permissions import can_manage_record, is_staff_role
from .serializers import (
    CoralRecordSerializer,
    CoralRecordUploadSerializer,
    SanctuarySerializer,
)


class IsStaffRoleOrReadOnly(permissions.BasePermission):
    """Editing/deleting an existing record (as opposed to creating a
    new one) is a CENRO staff / assigned sanctuary manager action — see
    monitoring/permissions.py."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return can_manage_record(request.user, obj)


class SanctuaryViewSet(viewsets.ReadOnlyModelViewSet):
    """Lists the marine sanctuaries, for populating the geomap and any
    sanctuary-filter dropdown in the frontend."""

    queryset = Sanctuary.objects.all()
    serializer_class = SanctuarySerializer
    permission_classes = [permissions.AllowAny]


class CoralRecordViewSet(viewsets.ModelViewSet):
    """
    list / retrieve: geomap data, filterable via query params:
        ?sanctuary=<id>
        ?label=healthy|bleached   (filters on the verified label if
                                    present, otherwise the prediction)
        ?since=<ISO datetime>     (records captured on/after this time)
    create: image submission endpoint — runs the trained classifier on
        the uploaded photo and stores the GPS-tagged result.
    """

    queryset = CoralRecord.objects.select_related("sanctuary").all()
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.action == "create":
            return CoralRecordUploadSerializer
        return CoralRecordSerializer

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated()]
        if self.action in ("update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), IsStaffRoleOrReadOnly()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        sanctuary_id = params.get("sanctuary")
        if sanctuary_id:
            qs = qs.filter(sanctuary_id=sanctuary_id)

        label = params.get("label")
        if label in ("healthy", "bleached"):
            qs = qs.filter(_effective_label_q(label))

        since = params.get("since")
        if since:
            parsed = parse_datetime(since)
            if parsed:
                qs = qs.filter(captured_at__gte=parsed)

        return qs

    def create(self, request, *args, **kwargs):
        # Override the default create() so the response reflects the
        # classification result, not just the fields the client submitted
        # — the diver needs to see "healthy" or "bleached" immediately
        # after uploading, not just have it silently stored.
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        instance = self._create_and_classify(write_serializer)

        read_serializer = CoralRecordSerializer(instance, context=self.get_serializer_context())
        headers = self.get_success_headers(read_serializer.data)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def _create_and_classify(self, serializer):
        photographer = self.request.user if self.request.user.is_authenticated else None

        # Save first with harmless placeholder classification fields so
        # the image file exists on disk (classify_image needs a real
        # path to read), then overwrite with the model's real output.
        instance = serializer.save(
            photographer=photographer,
            predicted_label="healthy",
            confidence=0.0,
        )

        result = ml_service.classify_image(instance.image.path)
        instance.predicted_label = result["label"]
        instance.confidence = result["probability"]
        instance.save(update_fields=["predicted_label", "confidence"])
        return instance


def _effective_label_q(label):
    """Q object matching CoralRecord.effective_label == label — i.e. the
    verified label if an expert has reviewed the record, otherwise the
    model's prediction."""
    from django.db.models import Q
    return Q(verified_label=label) | Q(verified_label__isnull=True, predicted_label=label)
