from django.urls import path

from apps.knowledge.views import SearchExpertsView, SearchKnowledgeView

urlpatterns = [
    path("knowledge/", SearchKnowledgeView.as_view(), name="search-knowledge"),
    path("experts/", SearchExpertsView.as_view(), name="search-experts"),
]
