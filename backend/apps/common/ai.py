"""
Embedding dual path: a real OpenAI embedding call when OPENAI_API_KEY is
configured, otherwise a deterministic, zero-cost, zero-network stub.

*** IMPORTANT: the stub embedding is NOT semantically meaningful. ***
It is a reproducible pseudo-random vector derived from a SHA-256 hash of the
input text, so the same text always produces the same vector (useful for
testing determinism, migrations, and ranking plumbing) - but it has no
relationship whatsoever to the text's actual meaning. Similarity search run
against stub embeddings will NOT return semantically relevant results; it's
only useful for verifying that the embed -> store (Qdrant) -> search
pipeline is wired correctly end to end. Real semantic search quality
requires setting OPENAI_API_KEY so get_embedding() calls the real OpenAI
embeddings API.
"""
import hashlib
import math
import random

from django.conf import settings


def _stub_embedding(text: str, dimensions: int) -> list[float]:
    """Deterministic, reproducible, NOT semantically meaningful vector."""
    seed = hashlib.sha256(text.encode("utf-8")).hexdigest()
    rng = random.Random(seed)
    vector = [rng.uniform(-1.0, 1.0) for _ in range(dimensions)]
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


def get_embedding(text: str) -> list[float]:
    """
    Return an embedding vector for `text`.

    Real path (OPENAI_API_KEY set): calls OpenAI's embeddings API using
    OPENAI_EMBEDDING_MODEL (default text-embedding-3-large), requesting
    EMBEDDING_DIMENSIONS via the API's `dimensions` param.

    Stub path (no key): deterministic pseudo-random vector, see module
    docstring - NOT semantically meaningful, just reproducible so the
    pipeline is fully testable without a key or network access.
    """
    dimensions = getattr(settings, "EMBEDDING_DIMENSIONS", 1536)
    api_key = getattr(settings, "OPENAI_API_KEY", "") or ""

    if not api_key:
        return _stub_embedding(text, dimensions)

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    model = getattr(settings, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
    response = client.embeddings.create(
        model=model,
        input=text,
        dimensions=dimensions,
    )
    return response.data[0].embedding
