"""
apps.ai_engine.views
Endpoint do agente incremental de BI.
"""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai_engine.serializers import CopilotGenerateSerializer, CopilotSQLPreviewSerializer
from apps.ai_engine.services.incremental_dashboard_agent import IncrementalDashboardAgentService
from apps.datasets.services.sqlite_query_service import LocalSQLiteQueryService, SQLiteQueryValidationError


class CopilotGenerateAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["ai"],
        summary="Gerar evolucao incremental de dashboard",
        request=CopilotGenerateSerializer,
    )
    def post(self, request):
        serializer = CopilotGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = IncrementalDashboardAgentService()
        try:
            result = service.generate(serializer.validated_data, request_user=request.user)
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class CopilotSQLPreviewAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["ai"],
        summary="Executar SQL preview em datasets do contexto (somente leitura)",
        request=CopilotSQLPreviewSerializer,
    )
    def post(self, request):
        serializer = CopilotSQLPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sql = serializer.validated_data["sql"]
        datasets = serializer.validated_data["datasets"]
        limit = serializer.validated_data.get("limit", 200)

        service = LocalSQLiteQueryService()
        try:
            result = service.execute_sql_for_datasets(datasets=datasets, sql=sql, limit=limit)
            return Response(result, status=status.HTTP_200_OK)
        except SQLiteQueryValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
