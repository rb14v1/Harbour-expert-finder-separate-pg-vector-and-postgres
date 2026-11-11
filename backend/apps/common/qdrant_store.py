"""
Thin wrapper around qdrant_client.QdrantClient - the vector-database half of
this app's two-database architecture (see README "Two databases, not
pgvector"). Postgres holds every relational/transactional row; Qdrant holds
nothing but embeddings + a small filterable payload, joined back to Postgres
by using the Django model's integer primary key directly as the Qdrant
point id. There is NO foreign-key/transactional consistency between the two
stores - apps/directory/signals.py and apps/knowledge/signals.py are what
keep them in sync on save/delete, and `manage.py sync_vectors`
(apps/common/management/commands/sync_vectors.py) is the from-scratch
recovery path if the Qdrant side is ever lost while Postgres survives.

Dev/test mode (QDRANT_URL unset): constructs
QdrantClient(location=":memory:") - qdrant-client's fully local, in-process
embedded mode. No server needed, and search/filter behavior is identical to
a real server; this is the equivalent of USE_SQLITE for the vector side.
A single client instance is cached at module scope (see `_get_client`) so
in-memory state persists across requests within one process, the same way a
real Qdrant server's state persists across requests.

Real mode (QDRANT_URL set): constructs QdrantClient(url=QDRANT_URL), talking
to an actual Qdrant server (docker-compose.yml's `qdrant` service).

Two collections are used (apps/directory/models.py, apps/knowledge/models.py):
    - "knowledge_entries": payload {visibility_departments, entry_type, author_id}
    - "employees": payload {department}
Both are EMBEDDING_DIMENSIONS-wide, Cosine distance.
"""
from django.conf import settings
from qdrant_client import QdrantClient
from qdrant_client.http import models

KNOWLEDGE_COLLECTION = "knowledge_entries"
EMPLOYEE_COLLECTION = "employees"

_client: QdrantClient | None = None


def _get_client() -> QdrantClient:
    global _client
    if _client is None:
        url = getattr(settings, "QDRANT_URL", "") or ""
        if url:
            _client = QdrantClient(url=url)
        else:
            _client = QdrantClient(location=":memory:")
    return _client


def reset_client() -> None:
    """Drop the cached client so the next call builds a fresh one. Mainly
    useful for tests that want a clean in-memory store between cases;
    production code never needs to call this."""
    global _client
    _client = None


def ensure_collection(collection: str) -> None:
    """Idempotent: create `collection` (vector size EMBEDDING_DIMENSIONS,
    Cosine distance) if it doesn't already exist."""
    client = _get_client()
    if not client.collection_exists(collection):
        dimensions = getattr(settings, "EMBEDDING_DIMENSIONS", 1536)
        client.create_collection(
            collection_name=collection,
            vectors_config=models.VectorParams(size=dimensions, distance=models.Distance.COSINE),
        )


def upsert_point(collection: str, point_id: int, vector: list[float], payload: dict) -> None:
    """Insert or replace the point with id `point_id` (the owning Django
    model's integer primary key) in `collection`."""
    ensure_collection(collection)
    client = _get_client()
    client.upsert(
        collection_name=collection,
        points=[models.PointStruct(id=point_id, vector=vector, payload=payload)],
    )


def search(
    collection: str,
    vector: list[float],
    top_k: int = 5,
    query_filter: dict | None = None,
) -> list[tuple[int, float]]:
    """Return up to `top_k` (point_id, score) pairs from `collection`,
    nearest-first. `query_filter`, if given, is a plain dict in Qdrant's
    filter JSON shape (e.g. {"should": [{"key": ..., "match": {"value": ...}}]}),
    converted here to a qdrant_client.http.models.Filter."""
    if top_k <= 0:
        return []
    ensure_collection(collection)
    client = _get_client()
    parsed_filter = models.Filter(**query_filter) if query_filter else None
    hits = client.search(
        collection_name=collection,
        query_vector=vector,
        query_filter=parsed_filter,
        limit=top_k,
    )
    return [(hit.id, hit.score) for hit in hits]


def delete_point(collection: str, point_id: int) -> None:
    """Delete a point by id. Idempotent: deleting an id that was never
    upserted (e.g. a Postgres row whose on_commit sync never ran - exactly
    what happens for every row created inside a Django TestCase, since its
    transaction is rolled back rather than committed) is treated as a no-op
    rather than an error, matching a real Qdrant server's delete semantics.
    qdrant-client's local/":memory:" engine, unlike a real server, raises a
    bare KeyError for an unknown id instead of a no-op - that's caught here."""
    ensure_collection(collection)
    client = _get_client()
    try:
        client.delete(collection_name=collection, points_selector=[point_id])
    except KeyError:
        pass


def get_point(collection: str, point_id: int):
    """Retrieve a single point (with payload/vector) by id, or None if it
    doesn't exist. Test-only convenience for asserting sync-on-save landed
    the right vector/payload."""
    ensure_collection(collection)
    client = _get_client()
    records = client.retrieve(collection_name=collection, ids=[point_id], with_vectors=True)
    return records[0] if records else None
