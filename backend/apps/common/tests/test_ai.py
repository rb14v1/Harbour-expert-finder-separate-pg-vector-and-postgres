from django.conf import settings
from django.test import TestCase

from apps.common.ai import get_embedding


class StubEmbeddingTests(TestCase):
    """No OPENAI_API_KEY is configured in the test environment, so
    get_embedding() must use the deterministic stub path."""

    def test_embedding_has_configured_dimensions(self):
        vector = get_embedding("Who knows about Kubernetes security?")
        self.assertEqual(len(vector), settings.EMBEDDING_DIMENSIONS)

    def test_embedding_is_deterministic_for_same_text(self):
        v1 = get_embedding("What is the remote work policy?")
        v2 = get_embedding("What is the remote work policy?")
        self.assertEqual(v1, v2)

    def test_embedding_differs_for_different_text(self):
        v1 = get_embedding("What is the remote work policy?")
        v2 = get_embedding("How do I expense a conference?")
        self.assertNotEqual(v1, v2)

    def test_embedding_is_l2_normalized(self):
        vector = get_embedding("Some arbitrary query text")
        norm = sum(x * x for x in vector) ** 0.5
        self.assertAlmostEqual(norm, 1.0, places=5)
