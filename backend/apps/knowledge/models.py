from django.db import models


class KnowledgeEntry(models.Model):
    """A policy document or Q&A entry. `visibility_departments` is a plain
    list of department-name strings: empty/null means visible to everyone,
    non-empty restricts visibility to those departments (see
    apps/knowledge/views.py get_queryset() and
    apps/knowledge/services/search.py search_knowledge() for the two places
    this is enforced - list/detail endpoints and semantic search). A plain
    JSONField is used rather than Postgres's ArrayField so this model works
    identically on SQLite (USE_SQLITE=True dev/test mode, see
    config/settings/base.py) and Postgres."""

    class EntryType(models.TextChoices):
        POLICY = "policy", "Policy"
        QNA = "qna", "Q&A"

    title = models.CharField(max_length=255)
    body = models.TextField()
    entry_type = models.CharField(max_length=20, choices=EntryType.choices, default=EntryType.QNA)
    author = models.ForeignKey(
        "directory.Employee", on_delete=models.CASCADE, related_name="knowledge_entries"
    )
    visibility_departments = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "knowledge entries"

    def __str__(self):
        return self.title[:60]

    @property
    def is_public(self) -> bool:
        return not self.visibility_departments

    def visible_to_department(self, department: str) -> bool:
        return self.is_public or department in self.visibility_departments
