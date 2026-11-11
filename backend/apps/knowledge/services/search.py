"""
Semantic search over the two Qdrant collections. Both functions embed the
query text with apps.common.ai.get_embedding, search Qdrant, then join the
resulting point ids back to Postgres rows - Qdrant never holds more than an
id + vector + small filterable payload (see apps/common/qdrant_store.py).
"""
from django.conf import settings

from apps.common import qdrant_store
from apps.common.ai import get_embedding
from apps.directory.models import Employee
from apps.knowledge.models import KnowledgeEntry


def _visibility_filter(department: str) -> dict:
    """Matches knowledge_entries points that are either public (empty
    visibility_departments) or explicitly include `department`."""
    return {
        "should": [
            {"key": "visibility_departments", "match": {"value": department}},
            {"is_empty": {"key": "visibility_departments"}},
        ]
    }


def _public_only_filter() -> dict:
    return {"must": [{"is_empty": {"key": "visibility_departments"}}]}


def search_knowledge(query_text: str, requesting_employee, top_k: int | None = None) -> list[dict]:
    """
    Embed `query_text`, search the knowledge_entries Qdrant collection
    filtered so results are either public or restricted to
    `requesting_employee`'s department, and return up to `top_k`
    {"entry": KnowledgeEntry, "score": float} dicts, nearest-first -
    the KnowledgeEntry rows are pulled back from Postgres by id.

    `requesting_employee` only needs a `.department` attribute - in
    practice this is the authenticated request.user (apps/knowledge/views.py),
    since not every user who can search the knowledge base necessarily has a
    linked Employee profile. Pass `None` for an hr_admin request: hr_admin
    sees every entry regardless of department, same as the list/detail
    endpoints (apps/knowledge/views.py KnowledgeEntryViewSet.get_queryset),
    so search applies no visibility filter at all in that case.
    """
    if top_k is None:
        top_k = getattr(settings, "SEARCH_TOP_K", 5)

    if requesting_employee is None:
        query_filter = None
    else:
        department = getattr(requesting_employee, "department", "") or ""
        query_filter = _visibility_filter(department) if department else _public_only_filter()

    vector = get_embedding(query_text)
    hits = qdrant_store.search(
        qdrant_store.KNOWLEDGE_COLLECTION, vector, top_k=top_k, query_filter=query_filter
    )

    entries_by_id = {
        entry.id: entry
        for entry in KnowledgeEntry.objects.select_related("author").filter(
            id__in=[point_id for point_id, _score in hits]
        )
    }
    results = []
    for point_id, score in hits:
        entry = entries_by_id.get(point_id)
        if entry is None:
            continue
        results.append({"entry": entry, "score": score})
    return results


def search_experts(query_text: str, top_k: int | None = None) -> list[dict]:
    """
    Embed `query_text`, search the org-wide employees Qdrant collection (no
    visibility restriction - the employee directory is visible to everyone),
    and return up to `top_k` {"employee": Employee, "score": float} dicts,
    nearest-first.
    """
    if top_k is None:
        top_k = getattr(settings, "SEARCH_TOP_K", 5)

    vector = get_embedding(query_text)
    hits = qdrant_store.search(qdrant_store.EMPLOYEE_COLLECTION, vector, top_k=top_k)

    employees_by_id = {
        employee.id: employee
        for employee in Employee.objects.filter(id__in=[point_id for point_id, _score in hits])
    }
    results = []
    for point_id, score in hits:
        employee = employees_by_id.get(point_id)
        if employee is None:
            continue
        results.append({"employee": employee, "score": score})
    return results
