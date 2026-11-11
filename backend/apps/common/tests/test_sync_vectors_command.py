"""Verifies `manage.py sync_vectors` (apps/common/management/commands/
sync_vectors.py) - the from-scratch recovery path for when the Qdrant side
of this app's two-database architecture is lost while Postgres survives
(see that command's docstring and the README)."""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.common import qdrant_store
from apps.directory.models import Employee
from apps.knowledge.models import KnowledgeEntry


class SyncVectorsCommandTests(TestCase):
    def setUp(self):
        self.author = Employee.objects.create(
            full_name="Recovery Author",
            department="Engineering",
            skills_summary="Recovery testing",
        )
        self.entry = KnowledgeEntry.objects.create(
            title="Recovery entry",
            body="Body text for recovery.",
            entry_type="qna",
            author=self.author,
        )

        # Simulate the Qdrant side being completely lost: delete any points
        # that may already be there (e.g. from the on_commit signal, which
        # wouldn't have fired here anyway under TestCase) before running the
        # command, so a pass here really does prove the command rebuilds
        # them from scratch rather than merely confirming pre-existing data.
        qdrant_store.delete_point(qdrant_store.EMPLOYEE_COLLECTION, self.author.id)
        qdrant_store.delete_point(qdrant_store.KNOWLEDGE_COLLECTION, self.entry.id)

    def test_command_rebuilds_both_collections_from_postgres(self):
        self.assertIsNone(qdrant_store.get_point(qdrant_store.EMPLOYEE_COLLECTION, self.author.id))
        self.assertIsNone(qdrant_store.get_point(qdrant_store.KNOWLEDGE_COLLECTION, self.entry.id))

        out = StringIO()
        call_command("sync_vectors", stdout=out)

        employee_point = qdrant_store.get_point(qdrant_store.EMPLOYEE_COLLECTION, self.author.id)
        entry_point = qdrant_store.get_point(qdrant_store.KNOWLEDGE_COLLECTION, self.entry.id)
        self.assertIsNotNone(employee_point)
        self.assertIsNotNone(entry_point)
        self.assertEqual(employee_point.payload["department"], "Engineering")
        self.assertEqual(entry_point.payload["author_id"], self.author.id)
        self.assertIn("Synced", out.getvalue())

    def test_command_is_idempotent(self):
        call_command("sync_vectors", stdout=StringIO())
        call_command("sync_vectors", stdout=StringIO())  # must not raise or duplicate

        employee_point = qdrant_store.get_point(qdrant_store.EMPLOYEE_COLLECTION, self.author.id)
        self.assertIsNotNone(employee_point)
