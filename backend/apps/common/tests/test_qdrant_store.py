from django.test import TestCase

from apps.common import qdrant_store
from apps.common.test_utils import pad_vector


class QdrantStoreTests(TestCase):
    """Each test uses its own collection, named after the test method. The
    in-memory Qdrant client is a module-level singleton (see
    qdrant_store._get_client) that does NOT participate in Django's
    per-test transaction rollback, unlike the Postgres/SQLite rows other
    tests create - so per-test collection names keep these cases from
    polluting each other, the same way Postgres's rollback keeps rows from
    leaking between tests."""

    def setUp(self):
        self.collection = f"test_qdrant_store__{self._testMethodName}"

    def test_ensure_collection_is_idempotent(self):
        qdrant_store.ensure_collection(self.collection)
        qdrant_store.ensure_collection(self.collection)  # must not raise

    def test_upsert_and_search_roundtrip(self):
        qdrant_store.upsert_point(
            self.collection, 101, pad_vector([1.0, 0.0, 0.0]), {"tag": "a"}
        )
        qdrant_store.upsert_point(
            self.collection, 102, pad_vector([0.0, 1.0, 0.0]), {"tag": "b"}
        )

        results = qdrant_store.search(self.collection, pad_vector([1.0, 0.0, 0.0]), top_k=2)
        ids = [point_id for point_id, _score in results]
        self.assertEqual(ids[0], 101)
        self.assertIn(102, ids)

    def test_search_top_k_limits_results(self):
        qdrant_store.upsert_point(self.collection, 201, pad_vector([1.0, 0.0]), {})
        qdrant_store.upsert_point(self.collection, 202, pad_vector([0.9, 0.1]), {})
        qdrant_store.upsert_point(self.collection, 203, pad_vector([0.0, 1.0]), {})

        results = qdrant_store.search(self.collection, pad_vector([1.0, 0.0]), top_k=1)
        self.assertEqual(len(results), 1)

    def test_search_top_k_zero_returns_empty(self):
        results = qdrant_store.search(self.collection, pad_vector([1.0, 0.0]), top_k=0)
        self.assertEqual(results, [])

    def test_delete_point_removes_from_search_results(self):
        qdrant_store.upsert_point(self.collection, 301, pad_vector([1.0, 0.0]), {})
        qdrant_store.delete_point(self.collection, 301)

        results = qdrant_store.search(self.collection, pad_vector([1.0, 0.0]), top_k=10)
        ids = [point_id for point_id, _score in results]
        self.assertNotIn(301, ids)

    def test_query_filter_restricts_results(self):
        qdrant_store.upsert_point(
            self.collection, 401, pad_vector([1.0, 0.0]), {"visibility_departments": []}
        )
        qdrant_store.upsert_point(
            self.collection, 402, pad_vector([0.95, 0.05]), {"visibility_departments": ["Finance"]}
        )

        query_filter = {
            "should": [
                {"key": "visibility_departments", "match": {"value": "Engineering"}},
                {"is_empty": {"key": "visibility_departments"}},
            ]
        }
        results = qdrant_store.search(
            self.collection, pad_vector([1.0, 0.0]), top_k=10, query_filter=query_filter
        )
        ids = [point_id for point_id, _score in results]
        self.assertIn(401, ids)
        self.assertNotIn(402, ids)

    def test_get_point_returns_payload_and_vector(self):
        qdrant_store.upsert_point(
            self.collection, 501, pad_vector([1.0, 0.0]), {"tag": "c"}
        )
        point = qdrant_store.get_point(self.collection, 501)
        self.assertIsNotNone(point)
        self.assertEqual(point.payload["tag"], "c")
        self.assertEqual(len(point.vector), len(pad_vector([1.0, 0.0])))

    def test_get_point_returns_none_for_missing_id(self):
        point = qdrant_store.get_point(self.collection, 999999)
        self.assertIsNone(point)
