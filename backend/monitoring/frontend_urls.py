from django.urls import path

from .frontend_views import MapView, RegisterView, UploadView

app_name = "monitoring"

urlpatterns = [
    path("", MapView.as_view(), name="map"),
    path("upload/", UploadView.as_view(), name="upload"),
    path("register/", RegisterView.as_view(), name="register"),
]