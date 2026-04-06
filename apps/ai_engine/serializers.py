"""
apps.ai_engine.serializers
Contrato de entrada do agente incremental de BI.
"""
from rest_framework import serializers


class CopilotGenerateSerializer(serializers.Serializer):
    dashboard_id = serializers.UUIDField(required=False, allow_null=True)
    project_id = serializers.UUIDField(required=False, allow_null=True)

    dashboardName = serializers.CharField(required=False, allow_blank=True, default="")
    reportTitle = serializers.CharField(required=False, allow_blank=True, default="")
    reportDescription = serializers.CharField(required=False, allow_blank=True, default="")

    dataDomain = serializers.CharField(required=False, allow_blank=True, default="")
    domainDataOwner = serializers.CharField(required=False, allow_blank=True, default="")
    dataConfidentiality = serializers.CharField(required=False, allow_blank=True, default="")

    crawlerFrequency = serializers.CharField(required=False, allow_blank=True, default="")

    sessionAuthor = serializers.CharField(required=False, allow_blank=True, default="")
    currentVersion = serializers.CharField(required=False, allow_blank=True, default="")
    currentDashboardState = serializers.CharField(required=False, allow_blank=True, default="")
    previousUserPrompts = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    currentUserPrompt = serializers.CharField(required=False, allow_blank=True, default="")

    templatePrompt = serializers.CharField(required=False, allow_blank=True, default="")
    masterPrompt = serializers.CharField(required=False, allow_blank=True, default="")
    reportMetadata = serializers.JSONField(required=False, default=dict)
    datasets = serializers.ListField(required=False, default=list)
    semanticRelationships = serializers.ListField(required=False, default=list)
    knowledgeBasePromptHints = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )
    existingDashboardHtml = serializers.CharField(required=False, allow_blank=True, default="")

    frontendComponentContract = serializers.JSONField(required=False, default=dict)
    visualLayoutRules = serializers.JSONField(required=False, default=dict)
    outputFormatRules = serializers.JSONField(required=False, default=dict)
    requireBedrock = serializers.BooleanField(required=False, default=False)

    query = serializers.CharField(required=False, allow_blank=True, default="")
    trace_id = serializers.UUIDField(required=False, allow_null=True)


class CopilotSQLPreviewSerializer(serializers.Serializer):
    sql = serializers.CharField(required=True, allow_blank=False)
    datasets = serializers.ListField(required=True, allow_empty=False)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=1000, default=200)
