"""
apps.dashboards.services.publish_service
──────────────────────────────────────────
Publicação de dashboards via S3 + CloudFront.
"""
import logging
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class PublishService:
    """Publica dashboards aprovados via S3 + CloudFront."""

    def publish_dashboard(self, dashboard, user) -> str:
        """
        Publica o dashboard atual no S3 e invalida cache CloudFront.

        Returns:
            URL pública do dashboard
        """
        version = dashboard.current_version
        if not version or not version.html_s3_path:
            raise ValueError("Versão sem HTML para publicar.")

        from apps.datasets.services.s3_service import S3Service
        s3 = S3Service()

        # Download do HTML da versão
        html_bytes = s3.download_from_path(version.html_s3_path)
        html_content = html_bytes.decode("utf-8")

        # Upload no caminho público
        public_key = f"published/{dashboard.project.tenant.slug}/{dashboard.id}/index.html"
        s3.upload_html(html_content, public_key)

        # URL cloudfront
        cf_domain = settings.CLOUDFRONT_DOMAIN
        if cf_domain:
            url = f"{cf_domain.rstrip('/')}/{public_key}"
        else:
            cf_domain = (
                f"https://{s3.dashboards_bucket}.s3.amazonaws.com"
            )
            url = f"{cf_domain}/{public_key}"

        # Invalidar cache CloudFront
        if settings.CLOUDFRONT_DISTRIBUTION_ID:
            self._invalidate_cloudfront(
                settings.CLOUDFRONT_DISTRIBUTION_ID,
                f"/{public_key}",
            )

        # Atualizar dashboard
        dashboard.status = "PUBLISHED"
        dashboard.cloudfront_url = url
        dashboard.s3_published_path = f"s3://{s3.dashboards_bucket}/{public_key}"
        dashboard.published_at = timezone.now()
        dashboard.published_by = user
        dashboard.save()

        logger.info(f"Dashboard publicado: {url}")
        return url

    def _invalidate_cloudfront(self, distribution_id: str, path: str):
        """Invalida cache CloudFront para o path publicado."""
        import boto3
        import time
        try:
            cf = boto3.client("cloudfront", region_name="us-east-1")
            cf.create_invalidation(
                DistributionId=distribution_id,
                InvalidationBatch={
                    "Paths": {"Quantity": 1, "Items": [path]},
                    "CallerReference": str(time.time()),
                },
            )
            logger.info(f"CloudFront invalidation criada para {path}")
        except Exception as e:
            logger.warning(f"Falha ao invalidar CloudFront: {e}")
