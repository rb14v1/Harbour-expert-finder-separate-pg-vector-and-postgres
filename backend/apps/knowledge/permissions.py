from rest_framework.permissions import SAFE_METHODS, BasePermission


class KnowledgeEntryPermission(BasePermission):
    """List/retrieve visibility is enforced at the queryset level (see
    apps/knowledge/views.py get_queryset()), so a non-visible entry 404s
    rather than 403s, same as every other cross-scope isolation case in this
    workspace. This class only governs writes:

    - create: the public-vs-restricted / qna-vs-policy rule is enforced in
      KnowledgeEntrySerializer.validate() (serializer-level, not just this
      permission class, per spec - a non-admin POSTing entry_type=policy or
      a non-empty visibility_departments gets a 400, not a 403).
    - update/destroy: hr_admin may edit/delete any entry; a non-admin may
      edit/delete only an entry they authored.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if request.user.role == "hr_admin":
            return True
        employee = getattr(request.user, "employee_profile", None)
        return employee is not None and obj.author_id == employee.id
