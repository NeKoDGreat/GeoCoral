from django.urls import path

from .frontend_views import (
    DashboardView,
    DiverHomeView,
    DiverSettingsView,
    LandingView,
    MapView,
    RegisterView,
    RoleHomeView,
    UploadView,
    VerifyRecordView,
)

app_name = "monitoring"

urlpatterns = [
    path("", LandingView.as_view(), name="landing"),
    path("map/", MapView.as_view(), name="map"),
    path("upload/", UploadView.as_view(), name="upload"),
    path("register/", RegisterView.as_view(), name="register"),
    path("workspace/", RoleHomeView.as_view(), name="role_home"),
    path("diver/", DiverHomeView.as_view(), name="diver_home"),
    path("diver/settings/", DiverSettingsView.as_view(), name="diver_settings"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("dashboard/verify/<int:pk>/", VerifyRecordView.as_view(), name="verify_record"),
]