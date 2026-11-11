from rest_framework import serializers

from apps.knowledge.models import KnowledgeEntry


class KnowledgeEntrySerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.full_name", read_only=True)
    author_department = serializers.CharField(source="author.department", read_only=True)

    class Meta:
        model = KnowledgeEntry
        fields = [
            "id",
            "title",
            "body",
            "entry_type",
            "author",
            "author_name",
            "author_department",
            "visibility_departments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "author", "author_name", "author_department", "created_at", "updated_at"]

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Title cannot be blank.")
        return value

    def validate_visibility_departments(self, value):
        if value in (None, ""):
            return []
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise serializers.ValidationError("visibility_departments must be a list of department name strings.")
        return value

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user

        if user.role != "hr_admin":
            entry_type = attrs.get("entry_type", getattr(self.instance, "entry_type", KnowledgeEntry.EntryType.QNA))
            visibility_departments = attrs.get(
                "visibility_departments", getattr(self.instance, "visibility_departments", [])
            )
            if entry_type != KnowledgeEntry.EntryType.QNA:
                raise serializers.ValidationError(
                    {"entry_type": "Only HR admins can create or edit policy entries."}
                )
            if visibility_departments:
                raise serializers.ValidationError(
                    {"visibility_departments": "Only HR admins can restrict visibility to specific departments."}
                )
        return attrs
