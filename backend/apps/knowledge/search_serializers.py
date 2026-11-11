from rest_framework import serializers


class ExpertContactSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    department = serializers.CharField()


class KnowledgeSearchResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    body = serializers.CharField()
    entry_type = serializers.CharField()
    score = serializers.FloatField()
    expert_contact = ExpertContactSerializer()


class ExpertSearchResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    department = serializers.CharField()
    title = serializers.CharField()
    skills_summary = serializers.CharField()
    score = serializers.FloatField()
