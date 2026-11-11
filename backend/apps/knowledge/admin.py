from django.contrib import admin

from apps.knowledge.models import KnowledgeEntry


@admin.register(KnowledgeEntry)
class KnowledgeEntryAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "entry_type", "author", "created_at"]
    list_filter = ["entry_type"]
    search_fields = ["title", "body"]
