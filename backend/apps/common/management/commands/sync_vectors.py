"""
Recovery path for this app's two-database architecture: Postgres and Qdrant
have no shared transaction (see apps/common/qdrant_store.py module
docstring), so if the Qdrant container/volume is ever lost while Postgres
data survives, every embedding would otherwise be gone for good. This
command re-embeds and re-upserts every existing Employee and KnowledgeEntry
row into Qdrant from scratch. Idempotent - upsert_point() replaces by id, so
running it repeatedly (or against a store that already has some of the
points) is safe.
"""
from django.core.management.base import BaseCommand

from apps.common import qdrant_store
from apps.common.ai import get_embedding
from apps.directory.models import Employee
from apps.knowledge.models import KnowledgeEntry


class Command(BaseCommand):
    help = "Re-embed and re-upsert every Employee and KnowledgeEntry row into Qdrant from scratch."

    def handle(self, *args, **options):
        employee_count = 0
        for employee in Employee.objects.all():
            text = f"{employee.skills_summary} {employee.bio}".strip() or employee.full_name
            vector = get_embedding(text)
            qdrant_store.upsert_point(
                qdrant_store.EMPLOYEE_COLLECTION,
                employee.id,
                vector,
                {"department": employee.department},
            )
            employee_count += 1

        entry_count = 0
        for entry in KnowledgeEntry.objects.all():
            text = f"{entry.title} {entry.body}"
            vector = get_embedding(text)
            qdrant_store.upsert_point(
                qdrant_store.KNOWLEDGE_COLLECTION,
                entry.id,
                vector,
                {
                    "visibility_departments": entry.visibility_departments or [],
                    "entry_type": entry.entry_type,
                    "author_id": entry.author_id,
                },
            )
            entry_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Synced {employee_count} employee(s) and {entry_count} knowledge entry(ies) to Qdrant."
            )
        )
