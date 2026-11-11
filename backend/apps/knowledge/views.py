from django.conf import settings
from rest_framework import permissions, serializers as drf_serializers, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.knowledge.models import KnowledgeEntry
from apps.knowledge.permissions import KnowledgeEntryPermission
from apps.knowledge.search_serializers import (
    ExpertSearchResultSerializer,
    KnowledgeSearchResultSerializer,
)
from apps.knowledge.serializers import KnowledgeEntrySerializer
from apps.knowledge.services.search import search_experts, search_knowledge


class KnowledgeEntryViewSet(viewsets.ModelViewSet):
    """
    CRUD for KnowledgeEntry. Visibility (list/retrieve) is filtered in
    Python rather than via a DB-level JSONField containment lookup, because
    Django's `contains`/`contained_by` JSONField lookups are Postgres/MySQL/
    MariaDB-only and this app must also run on SQLite (USE_SQLITE=True dev/
    test mode) - see config/settings/base.py. Dataset sizes here are small
    (an internal knowledge base), so filtering candidate rows in Python is
    fine and keeps the logic identical on both backends.

    Create/edit rules (enforced in KnowledgeEntrySerializer.validate(), not
    just here): hr_admin can create/edit any entry_type with any
    visibility_departments; a regular employee can only create/edit public
    (empty visibility_departments) entry_type=qna entries.
    """

    serializer_class = KnowledgeEntrySerializer
    permission_classes = [permissions.IsAuthenticated, KnowledgeEntryPermission]

    def get_queryset(self):
        qs = KnowledgeEntry.objects.select_related("author").all()
        user = self.request.user
        if user.role == "hr_admin":
            return qs
        department = user.department
        visible_ids = [entry.id for entry in qs if entry.visible_to_department(department)]
        return qs.filter(id__in=visible_ids)

    def perform_create(self, serializer):
        employee = getattr(self.request.user, "employee_profile", None)
        if employee is None:
            raise drf_serializers.ValidationError(
                {"detail": "No employee profile is linked to this account, so it cannot author knowledge entries."}
            )
        serializer.save(author=employee)


class SearchKnowledgeView(APIView):
    """GET /api/search/knowledge/?q=...&top_k=... - semantic search over
    KnowledgeEntry, scoped to entries visible to the requesting user's
    department (see apps/knowledge/services/search.py search_knowledge)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = (request.query_params.get("q") or "").strip()
        if not query:
            return Response({"detail": "Query parameter 'q' is required."}, status=status.HTTP_400_BAD_REQUEST)

        top_k = _parse_top_k(request)
        requesting_employee = None if request.user.role == "hr_admin" else request.user
        results = search_knowledge(query, requesting_employee, top_k=top_k)

        payload = [
            {
                "id": r["entry"].id,
                "title": r["entry"].title,
                "body": r["entry"].body,
                "entry_type": r["entry"].entry_type,
                "score": r["score"],
                "expert_contact": {
                    "id": r["entry"].author_id,
                    "name": r["entry"].author.full_name,
                    "department": r["entry"].author.department,
                },
            }
            for r in results
        ]
        serializer = KnowledgeSearchResultSerializer(payload, many=True)
        return Response(serializer.data)


class SearchExpertsView(APIView):
    """GET /api/search/experts/?q=...&top_k=... - semantic search over the
    org-wide Employee directory (see
    apps/knowledge/services/search.py search_experts)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = (request.query_params.get("q") or "").strip()
        if not query:
            return Response({"detail": "Query parameter 'q' is required."}, status=status.HTTP_400_BAD_REQUEST)

        top_k = _parse_top_k(request)
        results = search_experts(query, top_k=top_k)

        payload = [
            {
                "id": r["employee"].id,
                "full_name": r["employee"].full_name,
                "department": r["employee"].department,
                "title": r["employee"].title,
                "skills_summary": r["employee"].skills_summary,
                "score": r["score"],
            }
            for r in results
        ]
        serializer = ExpertSearchResultSerializer(payload, many=True)
        return Response(serializer.data)


def _parse_top_k(request) -> int:
    raw = request.query_params.get("top_k")
    if raw is None:
        return getattr(settings, "SEARCH_TOP_K", 5)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return getattr(settings, "SEARCH_TOP_K", 5)
    return value if value > 0 else getattr(settings, "SEARCH_TOP_K", 5)
