"""
Ranking-correctness tests for apps/knowledge/services/search.py, in the
style of ticket-triage/backend/apps/tickets/tests/test_vector_search.py:
hand-crafted, short vectors (padded to EMBEDDING_DIMENSIONS) are upserted
directly via qdrant_store, bypassing both get_embedding() (whose stub output
is not semantically meaningful - see apps/common/ai.py) and the model
save() signal (which TestCase's rolled-back transaction would swallow - see
apps/knowledge/tests/test_vector_sync.py), so similarity ordering is exact
and independent of either.

Each test class also patches qdrant_store.KNOWLEDGE_COLLECTION /
EMPLOYEE_COLLECTION to a private, per-class collection name. search_knowledge
/search_experts look these constants up as `qdrant_store.KNOWLEDGE_COLLECTION`
at call time (not a value bound at import time), so patching the attribute
redirects both this test's own upserts and search_knowledge/search_experts's
internal qdrant_store.search() call to the same private collection -
isolating these exact-order assertions from the real, shared
"knowledge_entries"/"employees" collections, which also hold seed-migration
data and whatever other test cases have upserted (see
apps/knowledge/tests/test_permissions_visibility.py and
apps/directory/tests/test_vector_sync.py, which write into the *real*
collections and so only ever assert membership, never exact order/count).

Because apps/common/ai.get_embedding() is monkeypatched to return the query
vector verbatim, these tests only verify qdrant_store + the
Postgres-rejoin/department-filter logic in search_knowledge/search_experts -
not get_embedding() itself (covered separately in
apps/common/tests/test_ai.py).
"""
from unittest import mock

from django.test import TestCase

from apps.common import qdrant_store
from apps.common.test_utils import pad_vector
from apps.directory.models import Employee
from apps.knowledge.models import KnowledgeEntry
from apps.knowledge.services.search import search_experts, search_knowledge


class FakeEmployee:
    def __init__(self, department):
        self.department = department


class SearchKnowledgeRankingTests(TestCase):
    def setUp(self):
        collection_patcher = mock.patch.object(
            qdrant_store, "KNOWLEDGE_COLLECTION", "test_search__knowledge_entries"
        )
        collection_patcher.start()
        self.addCleanup(collection_patcher.stop)

        self.author = Employee.objects.create(
            full_name="Search Author", department="Engineering", title="Engineer"
        )

        self.exact_match = KnowledgeEntry.objects.create(
            title="Exact match entry", body="body", entry_type="policy", author=self.author
        )
        self.close_match = KnowledgeEntry.objects.create(
            title="Close match entry", body="body", entry_type="policy", author=self.author
        )
        self.restricted_entry = KnowledgeEntry.objects.create(
            title="Restricted entry",
            body="body",
            entry_type="policy",
            author=self.author,
            visibility_departments=["Finance"],
        )

        for entry, vector, departments in [
            (self.exact_match, [1.0, 0.0, 0.0], []),
            (self.close_match, [0.9, 0.1, 0.0], []),
            (self.restricted_entry, [0.95, 0.05, 0.0], ["Finance"]),
        ]:
            qdrant_store.upsert_point(
                qdrant_store.KNOWLEDGE_COLLECTION,
                entry.id,
                pad_vector(vector),
                {
                    "visibility_departments": departments,
                    "entry_type": entry.entry_type,
                    "author_id": self.author.id,
                },
            )

        self.query_vector = pad_vector([1.0, 0.0, 0.0])
        embedding_patcher = mock.patch(
            "apps.knowledge.services.search.get_embedding", return_value=self.query_vector
        )
        embedding_patcher.start()
        self.addCleanup(embedding_patcher.stop)

    def test_results_ordered_nearest_first(self):
        results = search_knowledge("irrelevant query text", FakeEmployee("Finance"), top_k=10)
        ids_in_order = [r["entry"].id for r in results]
        self.assertEqual(
            ids_in_order,
            [self.exact_match.id, self.restricted_entry.id, self.close_match.id],
        )

    def test_scores_are_attached(self):
        results = search_knowledge("irrelevant query text", FakeEmployee("Finance"), top_k=10)
        scores = {r["entry"].id: r["score"] for r in results}
        self.assertAlmostEqual(scores[self.exact_match.id], 1.0, places=3)

    def test_requester_outside_department_excludes_restricted_entry(self):
        results = search_knowledge("irrelevant query text", FakeEmployee("Sales"), top_k=10)
        ids = [r["entry"].id for r in results]
        self.assertIn(self.exact_match.id, ids)
        self.assertIn(self.close_match.id, ids)
        self.assertNotIn(self.restricted_entry.id, ids)

    def test_requester_in_department_includes_restricted_entry(self):
        results = search_knowledge("irrelevant query text", FakeEmployee("Finance"), top_k=10)
        ids = [r["entry"].id for r in results]
        self.assertIn(self.restricted_entry.id, ids)

    def test_requester_with_no_employee_profile_sees_only_public(self):
        results = search_knowledge("irrelevant query text", FakeEmployee(""), top_k=10)
        ids = [r["entry"].id for r in results]
        self.assertIn(self.exact_match.id, ids)
        self.assertNotIn(self.restricted_entry.id, ids)

    def test_none_requester_bypasses_visibility_filter(self):
        results = search_knowledge("irrelevant query text", None, top_k=10)
        ids = [r["entry"].id for r in results]
        self.assertIn(self.restricted_entry.id, ids)

    def test_top_k_limits_result_count(self):
        results = search_knowledge("irrelevant query text", None, top_k=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["entry"].id, self.exact_match.id)


class SearchExpertsRankingTests(TestCase):
    def setUp(self):
        collection_patcher = mock.patch.object(
            qdrant_store, "EMPLOYEE_COLLECTION", "test_search__employees"
        )
        collection_patcher.start()
        self.addCleanup(collection_patcher.stop)

        self.security_expert = Employee.objects.create(
            full_name="Security Expert",
            department="Engineering",
            skills_summary="Security audits, penetration testing",
        )
        self.generalist = Employee.objects.create(
            full_name="Generalist",
            department="Engineering",
            skills_summary="General engineering",
        )
        self.unrelated_expert = Employee.objects.create(
            full_name="Unrelated Expert",
            department="Sales",
            skills_summary="Enterprise sales",
        )

        for employee, vector in [
            (self.security_expert, [1.0, 0.0, 0.0]),
            (self.generalist, [0.6, 0.4, 0.0]),
            (self.unrelated_expert, [0.0, 0.0, 1.0]),
        ]:
            qdrant_store.upsert_point(
                qdrant_store.EMPLOYEE_COLLECTION,
                employee.id,
                pad_vector(vector),
                {"department": employee.department},
            )

        self.query_vector = pad_vector([1.0, 0.0, 0.0])
        embedding_patcher = mock.patch(
            "apps.knowledge.services.search.get_embedding", return_value=self.query_vector
        )
        embedding_patcher.start()
        self.addCleanup(embedding_patcher.stop)

    def test_results_ordered_nearest_first(self):
        results = search_experts("who knows about security audits?", top_k=10)
        ids_in_order = [r["employee"].id for r in results]
        self.assertEqual(
            ids_in_order,
            [self.security_expert.id, self.generalist.id, self.unrelated_expert.id],
        )

    def test_no_department_restriction_applied(self):
        # search_experts has no visibility filtering at all - the directory
        # is org-wide, unlike knowledge entries.
        results = search_experts("who knows about security audits?", top_k=10)
        ids = [r["employee"].id for r in results]
        self.assertIn(self.unrelated_expert.id, ids)

    def test_top_k_limits_result_count(self):
        results = search_experts("who knows about security audits?", top_k=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["employee"].id, self.security_expert.id)
