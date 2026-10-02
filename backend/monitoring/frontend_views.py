"""
GeoCoral — server-rendered frontend pages.

Separate from monitoring/views.py (the DRF API viewsets). These pages
call that same API from client-side JS (see static/monitoring/js/).
"""

from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Case, Count, F, Q, When
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView

from .forms import DiverRegistrationForm
from .models import CoralRecord, Sanctuary
from .permissions import is_staff_role


class MapView(TemplateView):
    """Public geomapping view — anyone can browse classification
    results, matching the read-only API permissions."""
    template_name = "monitoring/map.html"


class UploadView(LoginRequiredMixin, TemplateView):
    """Photo submission page. Requires login since the upload API
    endpoint requires authentication (see CoralRecordViewSet)."""
    template_name = "monitoring/upload.html"
    login_url = "login"


class RegisterView(CreateView):
    """Public diver self-registration — deliberately separate from the
    Django admin's user management. Always creates a 'diver' role
    UserProfile (see DiverRegistrationForm); promoting someone to CENRO
    staff or sanctuary manager stays an admin-only action."""
    form_class = DiverRegistrationForm
    template_name = "registration/register.html"
    success_url = reverse_lazy("monitoring:upload")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)  # sign them in immediately after registering
        return response


class DashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """CENRO staff / sanctuary manager / admin dashboard: system-wide
    totals, a per-sanctuary breakdown, and expert verification of
    individual records. Divers do not have access — see is_staff_role.
    """
    template_name = "monitoring/dashboard.html"
    login_url = "login"

    def test_func(self):
        return is_staff_role(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # effective_label as a DB-level annotation, since the model
        # property (verified_label or predicted_label) can't be used
        # directly in aggregate queries.
        effective_label = Case(
            When(verified_label__isnull=False, then="verified_label"),
            default="predicted_label",
        )

        records = CoralRecord.objects.annotate(_effective_label=effective_label)

        total = records.count()
        bleached_count = records.filter(_effective_label="bleached").count()
        healthy_count = total - bleached_count
        verified_count = records.filter(verified_label__isnull=False).count()

        # Of the records an expert has actually reviewed, how often did
        # the model's original prediction match the expert's call?
        agreement_count = records.filter(
            verified_label__isnull=False
        ).filter(verified_label=F("predicted_label")).count()

        sanctuaries = Sanctuary.objects.annotate(
            total=Count("coral_records"),
            bleached=Count(
                "coral_records",
                filter=Q(coral_records__predicted_label="bleached", coral_records__verified_label__isnull=True)
                | Q(coral_records__verified_label="bleached"),
            ),
        ).order_by("name")

        context.update({
            "total_records": total,
            "healthy_count": healthy_count,
            "bleached_count": bleached_count,
            "bleached_pct": round(bleached_count / total * 100, 1) if total else 0,
            "verified_count": verified_count,
            "agreement_count": agreement_count,
            "agreement_pct": round(agreement_count / verified_count * 100, 1) if verified_count else None,
            "sanctuaries": sanctuaries,
            "records": records.select_related("sanctuary", "photographer").order_by("-captured_at")[:100],
        })
        return context


class VerifyRecordView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Handles the inline 'confirm healthy / confirm bleached' actions
    on the dashboard. POST-only; redirects back to the dashboard."""
    login_url = "login"

    def test_func(self):
        return is_staff_role(self.request.user)

    def post(self, request, *args, **kwargs):
        record = get_object_or_404(CoralRecord, pk=kwargs["pk"])
        label = request.POST.get("verified_label")
        if label in ("healthy", "bleached"):
            record.verified_label = label
            record.verified_by = request.user
            record.verified_at = timezone.now()
            record.save(update_fields=["verified_label", "verified_by", "verified_at"])
        return redirect("monitoring:dashboard")


class SpeciesTagView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Handles the species dropdown + submit on the dashboard. Manual
    tagging only — not AI-identified, see CoralRecord.SPECIES_CHOICES."""
    login_url = "login"

    def test_func(self):
        return is_staff_role(self.request.user)

    def post(self, request, *args, **kwargs):
        record = get_object_or_404(CoralRecord, pk=kwargs["pk"])
        species = request.POST.get("species")
        valid_choices = dict(CoralRecord.SPECIES_CHOICES)
        if species in valid_choices:
            record.species = species
            record.species_tagged_by = request.user
            record.species_tagged_at = timezone.now()
            record.save(update_fields=["species", "species_tagged_by", "species_tagged_at"])
        return redirect("monitoring:dashboard")