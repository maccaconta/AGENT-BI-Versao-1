"""
apps.dashboards.serializers
Serializers do módulo de dashboards.
"""
from rest_framework import serializers

from apps.dashboards.models import Dashboard, GenerationJob


class DashboardSerializer(serializers.ModelSerializer):
    project_name = serializers.ReadOnlyField(source="project.name")
    current_version_id = serializers.UUIDField(source="current_version.id", read_only=True)
    current_version_number = serializers.IntegerField(source="current_version.version_number", read_only=True)

    class Meta:
        model = Dashboard
        fields = [
            "id",
            "project",
            "project_name",
            "name",
            "description",
            "status",
            "instruction",
            "template",
            "current_version_id",
            "current_version_number",
            "cloudfront_url",
            "config",
            "tags",
            "is_public",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "status",
            "current_version_id",
            "current_version_number",
            "cloudfront_url",
            "created_at",
            "updated_at",
        ]


class DashboardCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dashboard
        fields = [
            "project",
            "name",
            "description",
            "instruction",
            "template",
            "config",
            "tags",
            "is_public",
        ]


class GenerateDashboardSerializer(serializers.Serializer):
    instruction = serializers.CharField(required=False, allow_blank=True, default="")
    dataset_id = serializers.UUIDField()
    template_id = serializers.UUIDField(required=False, allow_null=True)


class GenerationJobSerializer(serializers.ModelSerializer):
    dashboard_name = serializers.ReadOnlyField(source="dashboard.name")

    class Meta:
        model = GenerationJob
        fields = [
            "id",
            "dashboard",
            "dashboard_name",
            "status",
            "input_payload",
            "output_payload",
            "current_iteration",
            "max_iterations",
            "final_score",
            "error_details",
            "started_at",
            "finished_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
