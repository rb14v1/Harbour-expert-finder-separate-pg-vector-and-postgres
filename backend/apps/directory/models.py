from django.conf import settings
from django.db import models


class Employee(models.Model):
    """A directory profile: every entry shown in /api/search/experts/ and
    linkable as a KnowledgeEntry author. `user` is nullable/one-to-one on
    purpose - many people in the org directory (seeded for search variety)
    never log into this app at all, while a logged-in User who wants to
    author KnowledgeEntry rows needs a linked Employee profile (see
    apps/knowledge/views.py perform_create)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="employee_profile",
        null=True,
        blank=True,
    )
    full_name = models.CharField(max_length=255)
    department = models.CharField(max_length=100)
    title = models.CharField(max_length=150, blank=True, default="")
    skills_summary = models.TextField(blank=True, default="")
    bio = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name} ({self.department})"
