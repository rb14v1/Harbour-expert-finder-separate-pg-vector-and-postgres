from rest_framework import permissions, viewsets

from apps.directory.models import Employee
from apps.directory.permissions import IsHRAdminOrOwnProfile
from apps.directory.serializers import EmployeeSerializer


class EmployeeViewSet(viewsets.ModelViewSet):
    """Org-wide employee directory. Readable by every authenticated user;
    write access is gated by IsHRAdminOrOwnProfile (hr_admin: full CRUD on
    any profile; employee: update only the profile linked to their own
    account, no create/delete)."""

    queryset = Employee.objects.select_related("user").all()
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated, IsHRAdminOrOwnProfile]

    def perform_update(self, serializer):
        # Non-admins can edit their own skills/bio/title but never
        # re-point their profile at a different user account.
        if self.request.user.role != "hr_admin":
            serializer.validated_data.pop("user", None)
        serializer.save()
