"""Shared role-permission helpers, combined with queryset-level scoping in
each app's views (never serializer-only hiding) - see
apps/knowledge/views.py and apps/directory/views.py."""
from rest_framework.permissions import BasePermission


def user_role(request):
    user = getattr(request, "user", None)
    return getattr(user, "role", None)


class IsHRAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and user_role(request) == "hr_admin"
        )
