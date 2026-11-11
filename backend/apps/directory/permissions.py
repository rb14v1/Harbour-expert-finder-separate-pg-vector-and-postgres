from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsHRAdminOrOwnProfile(BasePermission):
    """Any authenticated user can read the directory (list/retrieve) - it's
    an org-wide resource. hr_admin can create/edit/delete any profile; a
    regular employee can edit only the Employee profile linked to their own
    account, and cannot create or delete profiles at all (directory upkeep
    beyond self-editing is HR's job)."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        if request.user.role == "hr_admin":
            return True
        # Non-admins may only reach update actions; create/destroy are
        # rejected here so they never get to has_object_permission.
        return view.action in ("update", "partial_update")

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if request.user.role == "hr_admin":
            return True
        return obj.user_id == request.user.id
