"""
apps.datasets.views
ViewSets para upload, processamento e consulta de datasets.
"""
import logging
import os
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.audit.signals import audit_event
from apps.datasets.models import Dataset, DatasetStatus
from apps.datasets.serializers import (
    DatasetCreateSerializer,
    DatasetSchemaSerializer,
    DatasetSerializer,
    PresignedUploadSerializer,
)
from apps.datasets.services.sqlite_query_service import (
    LocalSQLiteQueryService,
    SQLiteQueryValidationError,
)
from apps.datasets.services.sqlite_analytics_store import LocalSQLiteAnalyticsStoreService
from apps.datasets.tasks import process_dataset_task
from apps.users.permissions import IsTenantAnalyst, IsTenantMember, TenantObjectPermission

logger = logging.getLogger(__name__)


class DatasetViewSet(viewsets.ModelViewSet):
    """ViewSet para gerenciamento de datasets."""

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        qs = Dataset.objects.filter(is_deleted=False)
        if self.request.tenant:
            qs = qs.filter(project__tenant=self.request.tenant)
        project_id = self.request.query_params.get("project_id")
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs.select_related("project", "created_by")

    def get_serializer_class(self):
        if self.action == "create":
            return DatasetCreateSerializer
        return DatasetSerializer

    def get_permissions(self):
        if self.action in ["create", "upload", "update", "partial_update", "destroy"]:
            return [IsTenantAnalyst(), TenantObjectPermission()]
        return [IsTenantMember(), TenantObjectPermission()]

    def perform_create(self, serializer):
        dataset = serializer.save(created_by=self.request.user)
        audit_event.send(
            sender=self.__class__,
            action="dataset.created",
            user=self.request.user,
            tenant=self.request.tenant,
            resource_type="Dataset",
            resource_id=dataset.id,
        )

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[IsTenantAnalyst],
        url_path="upload",
    )
    def upload(self, request):
        """
        Faz upload de CSV/XLSX e dispara processamento.
        Em modo local (`USE_AWS_DATA_SERVICES=False`), salva o arquivo no disco local.
        Multipart form: file + project_id + name.
        """
        file = request.FILES.get("file")
        if not file:
            return Response(
                {"detail": "Arquivo nao enviado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.projects.models import Project

        project_id = request.data.get("project_id")
        try:
            project = Project.objects.get(
                id=project_id,
                tenant=request.tenant,
                is_deleted=False,
            )
        except Project.DoesNotExist:
            return Response(
                {"detail": "Projeto nao encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        ext = file.name.rsplit(".", 1)[-1].lower()
        if ext not in ["csv", "xlsx", "xls"]:
            return Response(
                {"detail": f"Extensao .{ext} nao suportada. Use CSV ou XLSX."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dataset_name = request.data.get("name", file.name.rsplit(".", 1)[0])
        use_aws_data = bool(getattr(settings, "USE_AWS_DATA_SERVICES", True))
        if use_aws_data:
            from apps.datasets.services.s3_service import S3Service

            s3 = S3Service()
            s3_key = f"{project.s3_path}/raw/{dataset_name}/{file.name}"
            try:
                s3_path = s3.upload_file(
                    file_obj=file,
                    s3_key=s3_key,
                    content_type=file.content_type,
                    metadata={
                        "original_filename": file.name,
                        "project_id": str(project.id),
                        "uploaded_by": str(request.user.id),
                    },
                )
            except Exception as exc:
                logger.error("Erro ao fazer upload S3: %s", exc)
                return Response(
                    {"detail": "Erro ao fazer upload. Tente novamente."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        else:
            try:
                s3_path = self._save_local_raw_file(
                    file_obj=file,
                    project_id=str(project.id),
                    dataset_name=dataset_name,
                )
            except Exception as exc:
                logger.error("Erro ao salvar arquivo local: %s", exc)
                return Response(
                    {"detail": "Erro ao salvar arquivo local para processamento."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        dataset = Dataset.objects.create(
            project=project,
            name=dataset_name,
            source_type="CSV" if ext == "csv" else "EXCEL",
            status=DatasetStatus.PENDING,
            s3_raw_path=s3_path,
            s3_original_filename=file.name,
            s3_original_size_bytes=file.size,
            glue_database=project.glue_database,
            created_by=request.user,
        )

        trace_id = request.data.get("trace_id")
        process_dataset_task.delay(str(dataset.id), trace_id=trace_id)

        audit_event.send(
            sender=self.__class__,
            action="dataset.uploaded",
            user=request.user,
            tenant=request.tenant,
            resource_type="Dataset",
            resource_id=dataset.id,
            extra={"filename": file.name, "size_bytes": file.size},
        )

        return Response(DatasetSerializer(dataset).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="presigned-upload")
    def presigned_upload(self, request):
        """Retorna URL pre-assinada para upload direto pelo browser."""
        if not bool(getattr(settings, "USE_AWS_DATA_SERVICES", True)):
            return Response(
                {"detail": "Presigned upload indisponivel no modo local sem AWS data services."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PresignedUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from apps.datasets.services.s3_service import S3Service

        s3 = S3Service()
        filename = serializer.validated_data["filename"]
        project_id = serializer.validated_data["project_id"]
        s3_key = f"tenant/{request.tenant.slug}/{project_id}/raw/{filename}"

        presigned = s3.generate_presigned_post(s3_key=s3_key)
        return Response({
            "upload_url": presigned["url"],
            "fields": presigned["fields"],
            "s3_key": s3_key,
        })

    @action(detail=True, methods=["post"], url_path="reprocess")
    def reprocess(self, request, pk=None):
        """Reinicia o processamento de um dataset."""
        dataset = self.get_object()
        dataset.status = DatasetStatus.PENDING
        dataset.processing_error = ""
        dataset.save()
        process_dataset_task.delay(str(dataset.id))
        return Response({"detail": "Reprocessamento iniciado."})

    @action(detail=True, methods=["get"], url_path="schema")
    def schema(self, request, pk=None):
        """Retorna schema detalhado do dataset."""
        dataset = self.get_object()
        return Response(DatasetSchemaSerializer(dataset).data)

    @action(detail=True, methods=["post"], url_path="sample-query")
    def sample_query(self, request, pk=None):
        """Executa query de amostra no Athena ou no SQLite local."""
        dataset = self.get_object()
        if not dataset.is_ready:
            return Response(
                {"detail": "Dataset ainda nao esta pronto para queries."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if self._should_use_sqlite(dataset):
            sql = f'SELECT * FROM "{self._sqlite_table_name(dataset)}" LIMIT {int(request.data.get("limit", 20))};'
            try:
                return Response(
                    self._sqlite_query_service().execute_sql_for_datasets(
                        datasets=[self._serialize_dataset_for_sqlite(dataset)],
                        sql=sql,
                        limit=int(request.data.get("limit", 20)),
                    )
                )
            except SQLiteQueryValidationError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        from apps.datasets.services.athena_service import AthenaQueryError, AthenaService

        athena = AthenaService()
        try:
            result = athena.get_sample_data(
                database=dataset.glue_database,
                table=dataset.glue_table,
                limit=request.data.get("limit", 20),
            )
            return Response(result.get("results", {}))
        except AthenaQueryError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="query-preview")
    def query_preview(self, request, pk=None):
        """Valida e executa SQL somente leitura usando o prototipo SQLite local."""
        dataset = self.get_object()
        sql = (request.data.get("sql") or "").strip()
        if not sql:
            return Response(
                {"detail": "Informe uma SQL para validacao."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = self._sqlite_query_service().execute_sql_for_datasets(
                datasets=[self._serialize_dataset_for_sqlite(dataset)],
                sql=sql,
                limit=int(request.data.get("limit", 50)),
            )
            return Response(result)
        except SQLiteQueryValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    def _should_use_sqlite(self, dataset: Dataset) -> bool:
        if not bool(getattr(settings, "USE_AWS_DATA_SERVICES", True)):
            return True
        engine = settings.DATABASES.get("default", {}).get("ENGINE", "")
        return "sqlite3" in engine or not (dataset.glue_database and dataset.glue_table)

    def _sqlite_table_name(self, dataset: Dataset) -> str:
        return self._sqlite_store_service().resolve_table_name(
            dataset_id=str(dataset.id),
            dataset_name=dataset.name,
        )

    def _sqlite_query_service(self) -> LocalSQLiteQueryService:
        return LocalSQLiteQueryService()

    def _sqlite_store_service(self) -> LocalSQLiteAnalyticsStoreService:
        return LocalSQLiteAnalyticsStoreService()

    def _serialize_dataset_for_sqlite(self, dataset: Dataset) -> dict:
        return {
            "id": str(dataset.id),
            "name": dataset.name,
            "sample_json": dataset.sample_json[:100] if isinstance(dataset.sample_json, list) else [],
            "schema_json": dataset.schema_json or {},
            "sqlite_table": self._sqlite_table_name(dataset),
            "row_count": dataset.row_count,
            "column_count": dataset.column_count,
        }

    def _save_local_raw_file(self, file_obj, project_id: str, dataset_name: str) -> str:
        base_dir = Path(str(getattr(settings, "LOCAL_DATA_DIR", Path(settings.BASE_DIR) / "local_data")))
        target_dir = base_dir / "raw" / project_id / dataset_name
        target_dir.mkdir(parents=True, exist_ok=True)

        safe_name = file_obj.name or f"dataset_{uuid4().hex}.csv"
        safe_name = os.path.basename(safe_name)
        target_file = target_dir / f"{uuid4().hex}_{safe_name}"

        with open(target_file, "wb") as output:
            for chunk in file_obj.chunks():
                output.write(chunk)

        return f"local://{target_file.as_posix()}"
