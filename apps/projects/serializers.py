from rest_framework import serializers

from .models import DataDomain, Project

class DataDomainSerializer(serializers.ModelSerializer):
    tenant_name = serializers.ReadOnlyField(source='tenant.name')
    owner_name = serializers.ReadOnlyField(source='owner.full_name')
    project_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = DataDomain
        fields = [
            'id', 'tenant', 'tenant_name', 'name', 
            'description', 'icon', 'owner', 'owner_name',
            'project_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class ProjectDomainSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listagem dentro de domínios"""
    class Meta:
        model = Project
        fields = ['id', 'name', 'status']


class ProjectSerializer(serializers.ModelSerializer):
    tenant_name = serializers.ReadOnlyField(source="tenant.name")
    domain_name = serializers.ReadOnlyField(source="domain.name")

    class Meta:
        model = Project
        fields = [
            "id",
            "tenant",
            "tenant_name",
            "domain",
            "domain_name",
            "name",
            "description",
            "domain_data_owner",
            "data_confidentiality",
            "crawler_frequency",
            "analysis_max_rows",
            "intake_metadata",
            "status",
            "s3_path",
            "glue_database",
            "athena_workgroup",
            "tags",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "data_ready",
            "pending_datasets_count",
        ]
        read_only_fields = [
            "id",
            "tenant",
            "tenant_name",
            "domain_name",
            "s3_path",
            "glue_database",
            "athena_workgroup",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "data_ready",
            "pending_datasets_count",
        ]

    data_ready = serializers.SerializerMethodField()
    pending_datasets_count = serializers.SerializerMethodField()

    def get_data_ready(self, obj) -> bool:
        from apps.datasets.models import DatasetStatus
        return not obj.datasets.filter(is_deleted=False).exclude(status=DatasetStatus.READY).exists()

    def get_pending_datasets_count(self, obj) -> int:
        from apps.datasets.models import DatasetStatus
        return obj.datasets.filter(is_deleted=False).exclude(status=DatasetStatus.READY).count()


class ProjectIntakeCreateSerializer(serializers.Serializer):
    dashboard = serializers.CharField(max_length=255)
    dataDomain = serializers.CharField(max_length=100)
    domainDataOwner = serializers.CharField(required=False, allow_blank=True, default="")
    confidentiality = serializers.CharField(required=False, allow_blank=True, default="")
    crawlFrequency = serializers.CharField(required=False, allow_blank=True, default="")
    objective = serializers.CharField(required=False, allow_blank=True, default="")
    specialist_prompt_id = serializers.UUIDField(required=False, allow_null=True)
    analysis_max_rows = serializers.IntegerField(required=False, default=5000)

    def validate_dashboard(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Informe um nome de dashboard para criar o projeto.")
        return cleaned

    def validate_dataDomain(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Informe o domínio de dados para criar o projeto.")
        return cleaned
