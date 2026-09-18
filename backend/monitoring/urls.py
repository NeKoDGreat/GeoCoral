from rest_framework.routers import DefaultRouter

from .views import CoralRecordViewSet, SanctuaryViewSet

router = DefaultRouter()
router.register(r"sanctuaries", SanctuaryViewSet, basename="sanctuary")
router.register(r"coral-records", CoralRecordViewSet, basename="coral-record")

urlpatterns = router.urls
