"""
apps.governance.serializers
───────────────────────────
Serializers para gestão de diretrizes e políticas de IA.
"""
from rest_framework import serializers
from apps.governance.models import GlobalSystemPrompt
from apps.shared_models import PromptTemplate


class PromptTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromptTemplate
        fields = [
            "id", "name", "description", "content", 
            "category", "variables", "is_public", "version"
        ]
        read_only_fields = ["id"]


class GlobalSystemPromptSerializer(serializers.ModelSerializer):
    """Serializer para as diretrizes mestras do Tenant."""
    created_by_name = serializers.ReadOnlyField(source="created_by.full_name")

    class Meta:
        model = GlobalSystemPrompt
        fields = [
            "id", "tenant", "persona_title", "persona_description",
            "style_guide", "compliance_rules", "language",
            "enable_temporal_profile", "enable_correlation_profile",
            "enable_anomaly_detection", "enable_clustering_profile",
            "enable_forecasting_profile", "max_tokens_limit",
            "ingestion_row_limit", "is_active", "created_by_name", 
            "created_at", "updated_at"
        ]
        read_only_fields = ["id", "tenant", "created_at", "updated_at"]
