"""
apps.datasets.serializers
─────────────────────────
Serializers para comunicação entre o motor de dados e o frontend.
"""
from rest_framework import serializers
from apps.datasets.models import Dataset, DatasetVersion


class DatasetSerializer(serializers.ModelSerializer):
    """Serializer completo para exibição e diagnóstico."""
    created_by_name = serializers.ReadOnlyField(source="created_by.first_name")
    is_ready = serializers.ReadOnlyField()

    class Meta:
        model = Dataset
        fields = [
            "id", "project", "name", "description", "source_type",
            "status", "s3_raw_path", "s3_parquet_path", 
            "s3_original_filename", "s3_original_size_bytes",
            "glue_table", "glue_database", "schema_json", "sample_json",
            "row_count", "column_count", "parquet_size_bytes",
            "processing_error", "processing_started_at", "processing_finished_at",
            "created_by_name", "is_ready", "created_at", "updated_at"
        ]
        read_only_fields = ["status", "s3_parquet_path", "glue_table", "schema_json", "sample_json"]


class DatasetCreateSerializer(serializers.ModelSerializer):
    """Serializer minimalista para criação inicial."""
    class Meta:
        model = Dataset
        fields = ["project", "name", "source_type", "s3_raw_path", "s3_original_filename", "s3_original_size_bytes"]


class DatasetSchemaSerializer(serializers.ModelSerializer):
    """Focado apenas no schema para o Diagnóstico do Agente."""
    class Meta:
        model = Dataset
        fields = ["id", "name", "schema_json", "sample_json", "status"]


class PresignedUploadSerializer(serializers.Serializer):
    """Parâmetros para solicitar URL pré-assinada de upload."""
    filename = serializers.CharField(max_length=500)
    project_id = serializers.UUIDField()
    content_type = serializers.CharField(max_length=100, required=False)
