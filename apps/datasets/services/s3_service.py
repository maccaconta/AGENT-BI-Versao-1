"""
apps.datasets.services.s3_service
───────────────────────────────────
Operações S3 para upload, download e gerenciamento do Data Lake.
"""
import io
import logging
from typing import Optional, BinaryIO
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError
from django.conf import settings

logger = logging.getLogger(__name__)


class S3Service:
    """Wrapper para operações S3 do Data Lake Agent-BI."""

    def __init__(self):
        kwargs = {
            "region_name": settings.AWS_REGION,
        }
        # MinIO local override
        if hasattr(settings, "S3_ENDPOINT_URL") and settings.S3_ENDPOINT_URL:
            kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL
            kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
            kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY

        self.client = boto3.client("s3", **kwargs)
        self.resource = boto3.resource("s3", **kwargs)
        self.datalake_bucket = settings.S3_DATALAKE_BUCKET
        self.dashboards_bucket = settings.S3_DASHBOARDS_BUCKET
        self.athena_bucket = settings.S3_ATHENA_RESULTS_BUCKET

    # ─── Upload ───────────────────────────────────────────────────────────────

    def upload_file(
        self,
        file_obj: BinaryIO,
        s3_key: str,
        bucket: Optional[str] = None,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Faz upload de um arquivo para o S3.
        Retorna o path completo: s3://{bucket}/{key}
        """
        bucket = bucket or self.datalake_bucket
        extra_args = {"ContentType": content_type}
        if metadata:
            extra_args["Metadata"] = {k: str(v) for k, v in metadata.items()}

        try:
            self.client.upload_fileobj(
                file_obj,
                bucket,
                s3_key,
                ExtraArgs=extra_args,
            )
            s3_path = f"s3://{bucket}/{s3_key}"
            logger.info(f"Upload S3: {s3_path}")
            return s3_path
        except ClientError as e:
            logger.error(f"Erro upload S3 {bucket}/{s3_key}: {e}")
            raise

    def upload_bytes(
        self,
        data: bytes,
        s3_key: str,
        bucket: Optional[str] = None,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload de bytes diretamente."""
        buffer = io.BytesIO(data)
        return self.upload_file(buffer, s3_key, bucket, content_type)

    def upload_html(self, html_content: str, s3_key: str) -> str:
        """Upload de HTML para o bucket de dashboards."""
        data = html_content.encode("utf-8")
        return self.upload_bytes(
            data, s3_key,
            bucket=self.dashboards_bucket,
            content_type="text/html; charset=utf-8",
        )

    # ─── Download ─────────────────────────────────────────────────────────────

    def download_file(self, s3_key: str, bucket: Optional[str] = None) -> bytes:
        """Download de arquivo do S3."""
        bucket = bucket or self.datalake_bucket
        try:
            response = self.client.get_object(Bucket=bucket, Key=s3_key)
            return response["Body"].read()
        except ClientError as e:
            logger.error(f"Erro download S3 {bucket}/{s3_key}: {e}")
            raise

    def download_from_path(self, s3_path: str) -> bytes:
        """Download a partir de um path s3:// completo."""
        parsed = urlparse(s3_path)
        bucket = parsed.netloc
        key = parsed.path.lstrip("/")
        return self.download_file(key, bucket)

    # ─── Presigned URLs ───────────────────────────────────────────────────────

    def generate_presigned_url(
        self,
        s3_key: str,
        bucket: Optional[str] = None,
        expiration: int = 3600,
        operation: str = "get_object",
    ) -> str:
        """Gera URL pré-assinada para download ou upload."""
        bucket = bucket or self.datalake_bucket
        try:
            return self.client.generate_presigned_url(
                operation,
                Params={"Bucket": bucket, "Key": s3_key},
                ExpiresIn=expiration,
            )
        except ClientError as e:
            logger.error(f"Erro ao gerar presigned URL: {e}")
            raise

    def generate_presigned_post(
        self,
        s3_key: str,
        bucket: Optional[str] = None,
        expiration: int = 3600,
        max_size_mb: int = 500,
    ) -> dict:
        """Gera URL pré-assinada para upload direto pelo cliente."""
        bucket = bucket or self.datalake_bucket
        conditions = [
            ["content-length-range", 1, max_size_mb * 1024 * 1024],
        ]
        return self.client.generate_presigned_post(
            bucket,
            s3_key,
            Conditions=conditions,
            ExpiresIn=expiration,
        )

    # ─── List & Delete ────────────────────────────────────────────────────────

    def list_objects(self, prefix: str, bucket: Optional[str] = None) -> list:
        """Lista objetos num prefixo S3."""
        bucket = bucket or self.datalake_bucket
        try:
            paginator = self.client.get_paginator("list_objects_v2")
            objects = []
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                objects.extend(page.get("Contents", []))
            return objects
        except ClientError as e:
            logger.error(f"Erro ao listar objetos S3: {e}")
            return []

    def delete_prefix(self, prefix: str, bucket: Optional[str] = None) -> int:
        """Remove todos os objetos com um prefixo."""
        bucket = bucket or self.datalake_bucket
        objects = self.list_objects(prefix, bucket)
        if not objects:
            return 0

        delete_keys = [{"Key": obj["Key"]} for obj in objects]
        response = self.client.delete_objects(
            Bucket=bucket,
            Delete={"Objects": delete_keys},
        )
        deleted = len(response.get("Deleted", []))
        logger.info(f"Deletados {deleted} objetos do prefixo {prefix}")
        return deleted

    # ─── Utility ──────────────────────────────────────────────────────────────

    def object_exists(self, s3_key: str, bucket: Optional[str] = None) -> bool:
        """Verifica se objeto existe no S3."""
        bucket = bucket or self.datalake_bucket
        try:
            self.client.head_object(Bucket=bucket, Key=s3_key)
            return True
        except ClientError:
            return False

    def get_object_metadata(self, s3_key: str, bucket: Optional[str] = None) -> dict:
        """Retorna metadados de um objeto S3."""
        bucket = bucket or self.datalake_bucket
        try:
            response = self.client.head_object(Bucket=bucket, Key=s3_key)
            return {
                "size_bytes": response["ContentLength"],
                "last_modified": response["LastModified"],
                "content_type": response.get("ContentType"),
                "metadata": response.get("Metadata", {}),
            }
        except ClientError:
            return {}

    def ensure_bucket_exists(self, bucket_name: str) -> bool:
        """Cria bucket se não existir (apenas para desenvolvimento com MinIO)."""
        try:
            self.client.head_bucket(Bucket=bucket_name)
            return True
        except ClientError:
            try:
                self.client.create_bucket(Bucket=bucket_name)
                logger.info(f"Bucket criado: {bucket_name}")
                return True
            except ClientError as e:
                logger.error(f"Erro ao criar bucket {bucket_name}: {e}")
                return False
