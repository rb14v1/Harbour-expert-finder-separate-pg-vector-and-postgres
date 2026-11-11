from rest_framework.routers import DefaultRouter

from apps.knowledge.views import KnowledgeEntryViewSet

router = DefaultRouter()
router.register(r"", KnowledgeEntryViewSet, basename="knowledgeentry")

urlpatterns = router.urls
