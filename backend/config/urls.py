from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.auth_urls")),
    path("api/", include("apps.accounts.urls")),
    path("api/employees/", include("apps.directory.urls")),
    path("api/knowledge-entries/", include("apps.knowledge.urls")),
    path("api/search/", include("apps.knowledge.search_urls")),
]
