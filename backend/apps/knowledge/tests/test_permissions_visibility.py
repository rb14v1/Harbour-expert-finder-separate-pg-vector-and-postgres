"""
The core cross-department isolation guarantee: an `employee` in department A
must never see a KnowledgeEntry restricted to department B, via the list
endpoint, the detail endpoint, OR /api/search/knowledge/ - while an
`hr_admin` sees everything, and a public entry is visible to everyone
regardless of department.

Qdrant points are upserted directly with hand-crafted, padded vectors
(bypassing the save() signal, which TestCase's non-committing transaction
would swallow anyway - see apps/directory/tests/test_vector_sync.py for the
captureOnCommitCallbacks alternative used to test the signal itself) so the
semantic-search half of this test is deterministic.
"""
from unittest import mock

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.common import qdrant_store
from apps.common.test_utils import auth_client, create_user, pad_vector
from apps.directory.models import Employee
from apps.knowledge.models import KnowledgeEntry


class CrossDepartmentVisibilityTests(APITestCase):
    def setUp(self):
        # The real /api/search/knowledge/ endpoint calls get_embedding() on
        # the request's free-text query. Its stub output (apps/common/ai.py)
        # is a reproducible but semantically meaningless high-dimensional
        # vector, which would make a hand-crafted low-dimensional test
        # vector's cosine similarity to it essentially random noise -
        # indistinguishable from whatever's already in the shared
        # "knowledge_entries" collection (seed-migration data, other tests).
        # Patching get_embedding to return our own crafted query vector
        # (matching self.public_entry's vector exactly) makes the ranking
        # deterministic: both entries below score ~0.95+ against it, which
        # no unrelated random-noise point can realistically reach.
        patcher = mock.patch(
            "apps.knowledge.services.search.get_embedding",
            return_value=pad_vector([1.0, 0.0, 0.0]),
        )
        self.addCleanup(patcher.stop)
        patcher.start()

        self.dept_a_user = create_user(
            email="a@example.com", role="employee", department="Engineering"
        )
        self.dept_b_user = create_user(
            email="b@example.com", role="employee", department="Finance"
        )
        self.hr_user = create_user(email="hr@example.com", role="hr_admin", department="HR")

        self.author = Employee.objects.create(full_name="Author Person", department="Finance")

        self.public_entry = KnowledgeEntry.objects.create(
            title="Public policy",
            body="Visible to everyone.",
            entry_type="policy",
            author=self.author,
            visibility_departments=[],
        )
        self.restricted_to_b = KnowledgeEntry.objects.create(
            title="Finance-only policy",
            body="Only Finance can see this.",
            entry_type="policy",
            author=self.author,
            visibility_departments=["Finance"],
        )

        # Seed Qdrant directly (bypassing the on_commit signal, which never
        # fires inside TestCase's rolled-back transaction) so
        # /api/search/knowledge/ has something deterministic to find.
        qdrant_store.upsert_point(
            qdrant_store.KNOWLEDGE_COLLECTION,
            self.public_entry.id,
            pad_vector([1.0, 0.0, 0.0]),
            {"visibility_departments": [], "entry_type": "policy", "author_id": self.author.id},
        )
        qdrant_store.upsert_point(
            qdrant_store.KNOWLEDGE_COLLECTION,
            self.restricted_to_b.id,
            pad_vector([0.95, 0.05, 0.0]),
            {
                "visibility_departments": ["Finance"],
                "entry_type": "policy",
                "author_id": self.author.id,
            },
        )

    # --- list/detail endpoints ---

    def test_dept_a_employee_cannot_see_restricted_entry_in_list(self):
        client = auth_client(self.dept_a_user)
        response = client.get(reverse("knowledgeentry-list"))
        ids = [row["id"] for row in response.data["results"]]
        self.assertIn(self.public_entry.id, ids)
        self.assertNotIn(self.restricted_to_b.id, ids)

    def test_dept_a_employee_cannot_retrieve_restricted_entry_directly(self):
        client = auth_client(self.dept_a_user)
        response = client.get(reverse("knowledgeentry-detail", args=[self.restricted_to_b.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_dept_b_employee_can_see_own_restricted_entry(self):
        client = auth_client(self.dept_b_user)
        response = client.get(reverse("knowledgeentry-list"))
        ids = [row["id"] for row in response.data["results"]]
        self.assertIn(self.restricted_to_b.id, ids)

    def test_hr_admin_sees_everything_in_list(self):
        client = auth_client(self.hr_user)
        response = client.get(reverse("knowledgeentry-list"))
        ids = [row["id"] for row in response.data["results"]]
        self.assertIn(self.public_entry.id, ids)
        self.assertIn(self.restricted_to_b.id, ids)

    def test_public_entry_visible_to_any_department(self):
        for user in (self.dept_a_user, self.dept_b_user, self.hr_user):
            client = auth_client(user)
            response = client.get(reverse("knowledgeentry-detail", args=[self.public_entry.id]))
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    # --- /api/search/knowledge/ ---

    def test_dept_a_employee_search_never_returns_restricted_entry(self):
        client = auth_client(self.dept_a_user)
        response = client.get(reverse("search-knowledge"), {"q": "policy", "top_k": 10})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [row["id"] for row in response.data]
        self.assertIn(self.public_entry.id, ids)
        self.assertNotIn(self.restricted_to_b.id, ids)

    def test_dept_b_employee_search_can_return_restricted_entry(self):
        client = auth_client(self.dept_b_user)
        response = client.get(reverse("search-knowledge"), {"q": "policy", "top_k": 10})
        ids = [row["id"] for row in response.data]
        self.assertIn(self.restricted_to_b.id, ids)
        self.assertIn(self.public_entry.id, ids)

    def test_hr_admin_search_sees_restricted_entry_too(self):
        # hr_admin's own department (HR) isn't Finance, yet hr_admin still
        # finds the Finance-restricted entry via search - the department
        # filter is bypassed entirely for hr_admin requests (see
        # apps/knowledge/views.py SearchKnowledgeView), matching the
        # list/detail "hr_admin sees everything" rule.
        client = auth_client(self.hr_user)
        response = client.get(reverse("search-knowledge"), {"q": "policy", "top_k": 10})
        ids = [row["id"] for row in response.data]
        self.assertIn(self.public_entry.id, ids)
        self.assertIn(self.restricted_to_b.id, ids)
