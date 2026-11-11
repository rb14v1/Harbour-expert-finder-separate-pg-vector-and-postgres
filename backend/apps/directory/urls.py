from rest_framework.routers import DefaultRouter

from apps.directory.views import EmployeeViewSet

router = DefaultRouter()
router.register(r"", EmployeeViewSet, basename="employee")

urlpatterns = router.urls
