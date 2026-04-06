"""
apps.datasets.services.glue_service
─────────────────────────────────────
Integração com AWS Glue para catalogação de dados.
"""
import logging
from typing import Optional
import boto3
from botocore.exceptions import ClientError
from django.conf import settings

logger = logging.getLogger(__name__)


class GlueService:
    """Operações com AWS Glue Data Catalog."""

    def __init__(self):
        self.client = boto3.client(
            "glue",
            region_name=settings.AWS_REGION,
        )
        self.crawler_role_arn = settings.GLUE_CRAWLER_ROLE_ARN

    # ─── Databases ────────────────────────────────────────────────────────────

    def ensure_database_exists(self, database_name: str) -> bool:
        """Cria database no Glue se não existir."""
        try:
            self.client.get_database(Name=database_name)
            return True
        except self.client.exceptions.EntityNotFoundException:
            try:
                self.client.create_database(
                    DatabaseInput={
                        "Name": database_name,
                        "Description": f"Agent-BI Database: {database_name}",
                    }
                )
                logger.info(f"Glue database criado: {database_name}")
                return True
            except ClientError as e:
                logger.error(f"Erro ao criar Glue database: {e}")
                return False

    def delete_database(self, database_name: str) -> bool:
        """Remove database do Glue."""
        try:
            self.client.delete_database(Name=database_name)
            return True
        except ClientError as e:
            logger.error(f"Erro ao deletar Glue database {database_name}: {e}")
            return False

    # ─── Crawlers ─────────────────────────────────────────────────────────────

    def create_crawler(
        self,
        crawler_name: str,
        database_name: str,
        s3_path: str,
        schedule: Optional[str] = None,
    ) -> bool:
        """Cria crawler para catalogar dados no S3."""
        try:
            self.client.create_crawler(
                Name=crawler_name,
                Role=self.crawler_role_arn,
                DatabaseName=database_name,
                Targets={
                    "S3Targets": [{"Path": s3_path}]
                },
                TablePrefix="",
                SchemaChangePolicy={
                    "UpdateBehavior": "UPDATE_IN_DATABASE",
                    "DeleteBehavior": "LOG",
                },
                RecrawlPolicy={"RecrawlBehavior": "CRAWL_EVERYTHING"},
                Configuration='{"Version": 1.0, "CrawlerOutput": {"Partitions": {"AddOrUpdateBehavior": "InheritFromTable"}}}',
                **({"Schedule": schedule} if schedule else {}),
            )
            logger.info(f"Crawler criado: {crawler_name}")
            return True
        except self.client.exceptions.AlreadyExistsException:
            logger.info(f"Crawler já existe: {crawler_name}")
            return True
        except ClientError as e:
            logger.error(f"Erro ao criar crawler {crawler_name}: {e}")
            return False

    def start_crawler(self, crawler_name: str) -> bool:
        """Inicia execução de um crawler."""
        try:
            self.client.start_crawler(Name=crawler_name)
            logger.info(f"Crawler iniciado: {crawler_name}")
            return True
        except self.client.exceptions.CrawlerRunningException:
            logger.info(f"Crawler já está rodando: {crawler_name}")
            return True
        except ClientError as e:
            logger.error(f"Erro ao iniciar crawler {crawler_name}: {e}")
            return False

    def get_crawler_status(self, crawler_name: str) -> Optional[str]:
        """Retorna status atual do crawler."""
        try:
            response = self.client.get_crawler(Name=crawler_name)
            crawler = response["Crawler"]
            last_crawl = crawler.get("LastCrawl", {})
            return {
                "state": crawler["State"],
                "last_crawl_status": last_crawl.get("Status"),
                "last_crawl_time": last_crawl.get("StartTime"),
                "error_message": last_crawl.get("ErrorMessage"),
            }
        except ClientError as e:
            logger.error(f"Erro ao obter status do crawler: {e}")
            return None

    # ─── Tables ───────────────────────────────────────────────────────────────

    def get_table(self, database_name: str, table_name: str) -> Optional[dict]:
        """Obtém definição de uma tabela no Glue."""
        try:
            response = self.client.get_table(
                DatabaseName=database_name,
                Name=table_name,
            )
            return response["Table"]
        except self.client.exceptions.EntityNotFoundException:
            return None
        except ClientError as e:
            logger.error(f"Erro ao obter tabela Glue: {e}")
            return None

    def list_tables(self, database_name: str) -> list:
        """Lista todas as tabelas de um database."""
        try:
            paginator = self.client.get_paginator("get_tables")
            tables = []
            for page in paginator.paginate(DatabaseName=database_name):
                tables.extend(page.get("TableList", []))
            return tables
        except ClientError as e:
            logger.error(f"Erro ao listar tabelas Glue: {e}")
            return []

    def get_table_schema(self, database_name: str, table_name: str) -> Optional[dict]:
        """
        Retorna schema da tabela no formato Agent-BI:
        {
            columns: [{name, type, nullable, comment}],
            partition_keys: [{name, type}]
        }
        """
        table = self.get_table(database_name, table_name)
        if not table:
            return None

        storage = table.get("StorageDescriptor", {})
        columns = [
            {
                "name": col["Name"],
                "type": col["Type"],
                "nullable": True,
                "comment": col.get("Comment", ""),
            }
            for col in storage.get("Columns", [])
        ]

        partition_keys = [
            {"name": pk["Name"], "type": pk["Type"]}
            for pk in table.get("PartitionKeys", [])
        ]

        return {
            "columns": columns,
            "partition_keys": partition_keys,
            "location": storage.get("Location", ""),
            "input_format": storage.get("InputFormat", ""),
            "table_type": table.get("TableType", ""),
        }

    def create_table_from_parquet(
        self,
        database_name: str,
        table_name: str,
        s3_location: str,
        columns: list,
        partition_keys: Optional[list] = None,
    ) -> bool:
        """Cria tabela Parquet no Glue manualmente (sem crawler)."""
        try:
            storage_descriptor = {
                "Columns": [
                    {"Name": col["name"], "Type": col["type"]}
                    for col in columns
                ],
                "Location": s3_location,
                "InputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
                "OutputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
                "SerdeInfo": {
                    "SerializationLibrary": "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe",
                    "Parameters": {"serialization.format": "1"},
                },
            }

            table_input = {
                "Name": table_name,
                "StorageDescriptor": storage_descriptor,
                "TableType": "EXTERNAL_TABLE",
                "Parameters": {
                    "classification": "parquet",
                    "compressionType": "none",
                },
            }

            if partition_keys:
                table_input["PartitionKeys"] = [
                    {"Name": pk["name"], "Type": pk["type"]}
                    for pk in partition_keys
                ]

            try:
                self.client.create_table(
                    DatabaseName=database_name,
                    TableInput=table_input,
                )
                logger.info(f"Tabela Glue criada: {database_name}.{table_name}")
            except self.client.exceptions.AlreadyExistsException:
                self.client.update_table(
                    DatabaseName=database_name,
                    TableInput=table_input,
                )
                logger.info(f"Tabela Glue atualizada: {database_name}.{table_name}")

            return True

        except ClientError as e:
            logger.error(f"Erro ao criar tabela Glue: {e}")
            return False
