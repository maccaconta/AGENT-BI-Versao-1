import shutil
from pathlib import Path

from django.conf import settings
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.datasets.models import Dataset, DatasetStatus
from apps.datasets.services.sqlite_analytics_store import (
    build_sqlite_table_name,
)
from apps.projects.models import Project
from apps.users.models import RoleChoices, Tenant, TenantMember, User


@override_settings(USE_AWS_DATA_SERVICES=False)
class DatasetLocalDemoFlowTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.temp_dir = Path(settings.BASE_DIR) / "local_data_test"
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.local_settings = self.settings(
            LOCAL_DATA_DIR=str(self.temp_dir),
            LOCAL_ANALYTICS_SQLITE_PATH=str(self.temp_dir / "analytics" / "agent_bi_analytics.sqlite"),
        )
        self.local_settings.enable()

        self.tenant = Tenant.objects.create(
            name="Tenant Demo Local",
            slug="tenant-demo-local",
            s3_prefix="tenant-demo-local",
            glue_database_prefix="demo_local",
            athena_workgroup="demo-local",
        )
        self.user = User.objects.create_user(
            username="demo-local-user",
            email="demo.local@example.com",
            password="StrongPassword123!",
            primary_tenant=self.tenant,
        )
        TenantMember.objects.create(
            user=self.user,
            tenant=self.tenant,
            role=RoleChoices.ANALYST,
            is_active=True,
        )
        self.project = Project.objects.create(
            tenant=self.tenant,
            name="Projeto Demo Local",
            description="Projeto para validar fluxo local sem AWS data services.",
            created_by=self.user,
        )
        self.client.force_authenticate(self.user)
        self.tenant_headers = {"HTTP_X_TENANT_SLUG": self.tenant.slug}

    def tearDown(self):
        self.local_settings.disable()
        shutil.rmtree(str(self.temp_dir), ignore_errors=True)
        super().tearDown()

    def test_upload_process_and_query_preview_in_local_mode(self):
        csv_content = b"region,revenue\nNorte,100\nSul,200\nNorte,150\n"
        upload_url = "/api/v1/datasets/datasets/upload/"
        response = self.client.post(
            upload_url,
            {
                "project_id": str(self.project.id),
                "name": "Vendas Demo",
                "file": self._uploaded_file("vendas.csv", csv_content),
            },
            format="multipart",
            **self.tenant_headers,
        )
        self.assertEqual(response.status_code, 201, response.data)

        dataset = Dataset.objects.get(id=response.data["id"])
        self.assertEqual(dataset.status, DatasetStatus.READY)
        self.assertTrue(dataset.s3_raw_path.startswith("local://"))
        self.assertTrue(dataset.s3_parquet_path.startswith("local://"))
        self.assertGreater(dataset.row_count, 0)
        self.assertGreater(dataset.column_count, 0)

        sample_query_url = f"/api/v1/datasets/datasets/{dataset.id}/sample-query/"
        sample_response = self.client.post(
            sample_query_url,
            {"limit": 2},
            format="json",
            **self.tenant_headers,
        )
        self.assertEqual(sample_response.status_code, 200, sample_response.data)
        self.assertIn("rows", sample_response.data)
        self.assertIn("columns", sample_response.data)
        self.assertLessEqual(sample_response.data.get("row_count", 0), 2)
        self.assertEqual(sample_response.data.get("engine"), "sqlite-analytics-local")

        sqlite_table = self._sqlite_table_name(dataset)
        query_preview_url = f"/api/v1/datasets/datasets/{dataset.id}/query-preview/"
        query_response = self.client.post(
            query_preview_url,
            {"sql": f'SELECT COUNT(*) AS total FROM "{sqlite_table}";'},
            format="json",
            **self.tenant_headers,
        )
        self.assertEqual(query_response.status_code, 200, query_response.data)
        self.assertEqual(query_response.data.get("row_count"), 1)
        self.assertIn("rows", query_response.data)
        self.assertGreaterEqual(query_response.data["rows"][0].get("total", 0), 1)

        parquet_local_path = Path(dataset.s3_parquet_path.replace("local://", "", 1))
        self.assertTrue(parquet_local_path.exists())
        analytics_db_path = Path(settings.LOCAL_ANALYTICS_SQLITE_PATH)
        self.assertTrue(analytics_db_path.exists())

    def test_presigned_upload_disabled_in_local_mode(self):
        response = self.client.post(
            "/api/v1/datasets/datasets/presigned-upload/",
            {"filename": "demo.csv", "project_id": str(self.project.id)},
            format="json",
            **self.tenant_headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("indisponivel", str(response.data).lower())

    def _uploaded_file(self, name: str, content: bytes):
        from django.core.files.uploadedfile import SimpleUploadedFile

        return SimpleUploadedFile(name=name, content=content, content_type="text/csv")

    def _sqlite_table_name(self, dataset: Dataset) -> str:
        return build_sqlite_table_name(str(dataset.id), dataset.name)
