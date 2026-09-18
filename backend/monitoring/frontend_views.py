"""
GeoCoral — server-rendered frontend pages.

Separate from monitoring/views.py (the DRF API viewsets). These pages
call that same API from client-side JS (see static/monitoring/js/).
"""

from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView

from .forms import DiverRegistrationForm


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