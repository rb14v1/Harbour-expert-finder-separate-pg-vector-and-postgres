from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "full_name", "role", "department", "date_joined"]
        read_only_fields = fields


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adds role/department to the JWT claims as a frontend convenience.
    Every request is still re-validated server-side (IsAuthenticated +
    request.user.role/.department re-read from the DB), so a stale/tampered
    claim can't grant extra access - these claims are display-only."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["role"] = user.role
        token["department"] = user.department
        return token
