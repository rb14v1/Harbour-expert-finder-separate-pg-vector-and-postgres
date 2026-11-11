from django.test import TestCase

from apps.common import qdrant_store
from apps.directory.models import Employee
from apps.knowledge.models import KnowledgeEntry


class KnowledgeEntryVectorSyncTests(TestCase):
    """Verifies the post_save/post_delete signals in apps/knowledge/signals.py
    actually land (and remove) points in the "knowledge_entries" Qdrant
    collection. See apps/directory/tests/test_vector_sync.py for why
    captureOnCommitCallbacks is needed under TestCase."""

    def setUp(self):
        self.author = Employee.objects.create(full_name="Author Person", department="Engineering")

    def test_save_upserts_point_into_knowledge_entries_collection(self):
        with self.captureOnCommitCallbacks(execute=True):
            entry = KnowledgeEntry.objects.create(
                title="Sync Test Entry",
                body="Some policy body text.",
                entry_type="policy",
                author=self.author,
                visibility_departments=["Engineering"],
            )

        point = qdrant_store.get_point(qdrant_store.KNOWLEDGE_COLLECTION, entry.id)
        self.assertIsNotNone(point)
        self.assertEqual(point.payload["entry_type"], "policy")
        self.assertEqual(point.payload["visibility_departments"], ["Engineering"])
        self.assertEqual(point.payload["author_id"], self.author.id)
        self.assertEqual(len(point.vector), 1536)

    def test_update_re_syncs_point(self):
        with self.captureOnCommitCallbacks(execute=True):
            entry = KnowledgeEntry.objects.create(
                title="Sync Update Entry",
                body="Original body.",
                entry_type="qna",
                author=self.author,
            )

        with self.captureOnCommitCallbacks(execute=True):
            entry.visibility_departments = ["Finance"]
            entry.save()

        point = qdrant_store.get_point(qdrant_store.KNOWLEDGE_COLLECTION, entry.id)
        self.assertIsNotNone(point)
        self.assertEqual(point.payload["visibility_departments"], ["Finance"])

    def test_delete_removes_point(self):
        with self.captureOnCommitCallbacks(execute=True):
            entry = KnowledgeEntry.objects.create(
                title="Sync Delete Entry",
                body="Body.",
                entry_type="qna",
                author=self.author,
            )
        entry_id = entry.id
        self.assertIsNotNone(qdrant_store.get_point(qdrant_store.KNOWLEDGE_COLLECTION, entry_id))

        entry.delete()

        self.assertIsNone(qdrant_store.get_point(qdrant_store.KNOWLEDGE_COLLECTION, entry_id))
