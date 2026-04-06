"""
apps.datasets.models
─────────────────────
Dataset: fonte de dados ingerida, processada e catalogada no Glue.
"""
import uuid
from django.db import models
from apps.users.models import TimeStampedModel, User
from apps.projects.models import Project


class DatasetSourceType(models.TextChoices):
    CSV = "CSV", "CSV"
    EXCEL = "EXCEL", "Excel (XLSX)"
    SQL = "SQL", "SQL Connection"
    S3 = "S3", "S3 Path"
    API = "API", "API REST"


class DatasetStatus(models.TextChoices):
    PENDING = "PENDING", "Pendente"
    PROCESSING = "PROCESSING", "Processando"
    READY = "READY", "Pronto"
    ERROR = "ERROR", "Erro"
    OUTDATED = "OUTDATED", "Desatualizado"


class Dataset(TimeStampedModel):
    """
    Dataset ingerido e processado.
    Raw → Parquet → Glue Catalog → Athena.
    """
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="datasets",
        verbose_name="Projeto",
    )
    name = models.CharField(max_length=255, verbose_name="Nome")
    description = models.TextField(blank=True)
    source_type = models.CharField(
        max_length=20,
        choices=DatasetSourceType.choices,
        default=DatasetSourceType.CSV,
    )
    status = models.CharField(
        max_length=20,
        choices=DatasetStatus.choices,
        default=DatasetStatus.PENDING,
    )

    # S3 paths
    s3_raw_path = models.CharField(
        max_length=1000, blank=True,
        verbose_name="Path S3 Raw",
        help_text="Caminho do arquivo original no S3",
    )
    s3_parquet_path = models.CharField(
        max_length=1000, blank=True,
        verbose_name="Path S3 Parquet",
        help_text="Caminho dos arquivos Parquet processados",
    )
    s3_original_filename = models.CharField(max_length=500, blank=True)
    s3_original_size_bytes = models.BigIntegerField(default=0)

    # Glue
    glue_table = models.CharField(
        max_length=255, blank=True, verbose_name="Glue Table"
    )
    glue_database = models.CharField(
        max_length=255, blank=True, verbose_name="Glue Database"
    )
    glue_crawler_name = models.CharField(max_length=255, blank=True)
    last_crawled_at = models.DateTimeField(null=True, blank=True)

    # Schema & Sample
    schema_json = models.JSONField(
        default=dict, blank=True,
        verbose_name="Schema",
        help_text="Schema inferido: {columns: [{name, type, nullable}]}",
    )
    sample_json = models.JSONField(
        default=list, blank=True,
        verbose_name="Amostra de Dados",
        help_text="Primeiras 100 linhas para diagnóstico instantâneo.",
    )
    data_profile_json = models.JSONField(
        default=dict, blank=True,
        verbose_name="Perfil Estatístico",
        help_text=(
            "Perfil por coluna gerado na ingestão: distribuições, top valores, "
            "média/min/max para numericas. Usado como contexto compacto para a LLM."
        ),
    )
    row_count = models.BigIntegerField(default=0)
    column_count = models.IntegerField(default=0)
    parquet_size_bytes = models.BigIntegerField(default=0)

    # Processing
    processing_error = models.TextField(blank=True)
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processing_finished_at = models.DateTimeField(null=True, blank=True)

    # SQL connection (para source_type=SQL)
    sql_connection_secret_arn = models.CharField(
        max_length=500, blank=True,
        verbose_name="Secret ARN da Conexão SQL",
    )
    sql_query = models.TextField(
        blank=True,
        verbose_name="Query SQL de Extração",
    )

    # Metadata
    tags = models.JSONField(default=list, blank=True)
    partition_columns = models.JSONField(
        default=list, blank=True,
        verbose_name="Colunas de Partição",
    )

    # Audit
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name="created_datasets",
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="updated_datasets",
    )

    class Meta:
        db_table = "datasets"
        verbose_name = "Dataset"
        verbose_name_plural = "Datasets"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.project.name})"

    @property
    def is_ready(self):
        return self.status == DatasetStatus.READY

    @property
    def athena_table_ref(self):
        """Referência completa para Athena: database.table"""
        if self.glue_database and self.glue_table:
            return f"`{self.glue_database}`.`{self.glue_table}`"
        return None

    @property
    def column_names(self):
        """Lista de nomes de colunas do schema."""
        columns = self.schema_json.get("columns", [])
        return [col["name"] for col in columns]


class DatasetVersion(TimeStampedModel):
    """
    Snapshot de uma versão do dataset (dados + schema).
    Permite reprodutibilidade de dashboards.
    """
    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    version_number = models.PositiveIntegerField()
    s3_parquet_path = models.CharField(max_length=1000)
    schema_json = models.JSONField(default=dict)
    row_count = models.BigIntegerField(default=0)
    is_current = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True
    )

    class Meta:
        db_table = "dataset_versions"
        unique_together = [("dataset", "version_number")]
        ordering = ["-version_number"]

    def __str__(self):
        return f"{self.dataset.name} v{self.version_number}"
