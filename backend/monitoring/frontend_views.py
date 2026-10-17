"""
GeoCoral — server-rendered frontend pages.

Separate from monitoring/views.py (the DRF API viewsets). These pages
call that same API from client-side JS (see static/monitoring/js/).
"""

from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Case, Count, F, Q, When
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import FormView, TemplateView
from django.views.generic.edit import CreateView

from .forms import DiverAccountSettingsForm, DiverRegistrationForm
from .models import CoralRecord, Sanctuary
from .permissions import can_manage_record, get_user_role, is_staff_role


class LandingView(TemplateView):
    """Welcome page for guests; send signed-in users to their workspace."""
    template_name = "monitoring/landing.html"

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("monitoring:role_home")
        return super().get(request, *args, **kwargs)


class MapView(LoginRequiredMixin, TemplateView):
    """Authenticated geomapping view for browsing classification results."""
    template_name = "monitoring/map.html"
    login_url = "login"


class UploadView(LoginRequiredMixin, TemplateView):
    """Photo submission page. Requires login since the upload API
    endpoint requires authentication (see CoralRecordViewSet)."""
    template_name = "monitoring/upload.html"
    login_url = "login"


class RoleHomeView(LoginRequiredMixin, TemplateView):
    """Send each authenticated user to the interface for their application role."""
    login_url = "login"

    def get(self, request, *args, **kwargs):
        role = get_user_role(request.user)
        if role == "diver":
            return redirect("monitoring:diver_home")
        if role in ("cenro_staff", "sanctuary_manager"):
            return redirect("monitoring:dashboard")
        raise PermissionDenied("Your account does not have an application role.")


class DiverHomeView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Diver workspace with the photo-submission entry point and own history."""
    template_name = "monitoring/roles/diver/home.html"
    login_url = "login"

    def test_func(self):
        return get_user_role(self.request.user) == "diver"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["records"] = CoralRecord.objects.filter(
            photographer=self.request.user
        ).select_related("sanctuary")[:50]
        return context


class DiverSettingsView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    """Allow divers to update their account details."""
    template_name = "monitoring/roles/diver/settings.html"
    form_class = DiverAccountSettingsForm
    success_url = reverse_lazy("monitoring:diver_settings")
    login_url = "login"

    def test_func(self):
        return get_user_role(self.request.user) == "diver"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class RegisterView(CreateView):
    """Public diver self-registration — deliberately separate from the
    system operator's account management. Always creates a 'diver' role
    UserProfile (see DiverRegistrationForm)."""
    form_class = DiverRegistrationForm
    template_name = "registration/register.html"
    success_url = reverse_lazy("monitoring:diver_home")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)  # sign them in immediately after registering
        return response


class DashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """CENRO and sanctuary-manager dashboards, scoped to each role.

    CENRO sees all records; managers only see assigned sanctuaries.
    Divers use their separate workspace.
    """
    template_name = "monitoring/roles/cenro/dashboard.html"
    login_url = "login"

    def get_template_names(self):
        if get_user_role(self.request.user) == "sanctuary_manager":
            return ["monitoring/roles/sanctuary_manager/dashboard.html"]
        return [self.template_name]

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
        role = get_user_role(self.request.user)
        if role == "sanctuary_manager":
            assigned_sanctuaries = self.request.user.profile.assigned_sanctuaries.all()
            records = records.filter(sanctuary__in=assigned_sanctuaries)
        else:
            assigned_sanctuaries = Sanctuary.objects.all()

        total = records.count()
        bleached_count = records.filter(_effective_label="bleached").count()
        healthy_count = total - bleached_count
        verified_count = records.filter(verified_label__isnull=False).count()

        # Of the records an expert has actually reviewed, how often did
        # the model's original prediction match the expert's call?
        agreement_count = records.filter(
            verified_label__isnull=False
        ).filter(verified_label=F("predicted_label")).count()

        sanctuaries = assigned_sanctuaries.annotate(
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
            "pending_count": total - verified_count,
            "sanctuaries": sanctuaries,
            "records": records.select_related("sanctuary", "photographer").order_by("-captured_at")[:100],
            "is_sanctuary_manager": role == "sanctuary_manager",
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
        if not can_manage_record(request.user, record):
            raise PermissionDenied("You cannot manage records for this sanctuary.")
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