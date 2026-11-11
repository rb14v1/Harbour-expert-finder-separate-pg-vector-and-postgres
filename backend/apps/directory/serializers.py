from rest_framework import serializers

from apps.accounts.models import User
from apps.directory.models import Employee


class EmployeeSerializer(serializers.ModelSerializer):
    user_id = serializers.PrimaryKeyRelatedField(
        source="user", queryset=User.objects.all(), write_only=True, required=False, allow_null=True
    )
    user_email = serializers.SerializerMethodField()

    def get_user_email(self, obj):
        return obj.user.email if obj.user_id else None

    class Meta:
        model = Employee
        fields = [
            "id",
            "user_id",
            "user_email",
            "full_name",
            "department",
            "title",
            "skills_summary",
            "bio",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user_email", "created_at", "updated_at"]

    def validate_full_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Full name cannot be blank.")
        return value
