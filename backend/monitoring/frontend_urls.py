from django.urls import path

from .frontend_views import DashboardView, MapView, RegisterView, UploadView, VerifyRecordView

app_name = "monitoring"

urlpatterns = [
    path("", MapView.as_view(), name="map"),
    path("upload/", UploadView.as_view(), name="upload"),
    path("register/", RegisterView.as_view(), name="register"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("dashboard/verify/<int:pk>/", VerifyRecordView.as_view(), name="verify_record"),
]