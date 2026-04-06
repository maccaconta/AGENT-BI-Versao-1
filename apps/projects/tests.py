from rest_framework.test import APITestCase

from apps.projects.models import DataDomain, Project
from apps.users.models import RoleChoices, Tenant, TenantMember, User


class ProjectIntakeCreateTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(
            name="Tenant Intake",
            slug="tenant-intake",
            s3_prefix="tenant-intake",
            glue_database_prefix="tenant_intake",
            athena_workgroup="tenant-intake-wg",
        )
        self.user = User.objects.create_user(
            username="intake-user",
            email="intake.user@example.com",
            password="StrongPassword123!",
            primary_tenant=self.tenant,
        )
        TenantMember.objects.create(
            user=self.user,
            tenant=self.tenant,
            role=RoleChoices.ANALYST,
            is_active=True,
        )
        self.client.force_authenticate(self.user)
        self.tenant_headers = {"HTTP_X_TENANT_SLUG": self.tenant.slug}

    def test_create_project_persists_front_metadata_and_returns_uuid(self):
        payload = {
            "dashboard": "Cockpit Executivo Vendas",
            "dataDomain": "Varejo e Comercial",
            "domainDataOwner": "owner@empresa.com",
            "confidentiality": "Confidencial",
            "crawlFrequency": "Batch Diario",
            "objective": "Analisar vendas por canal e regiao.",
        }

        response = self.client.post(
            "/api/v1/projects/projects/",
            payload,
            format="json",
            **self.tenant_headers,
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["name"], payload["dashboard"])
        self.assertEqual(response.data["domain_data_owner"], payload["domainDataOwner"])
        self.assertEqual(response.data["data_confidentiality"], payload["confidentiality"])
        self.assertEqual(response.data["crawler_frequency"], payload["crawlFrequency"])

        project = Project.objects.get(id=response.data["id"])
        self.assertEqual(project.tenant, self.tenant)
        self.assertEqual(project.created_by, self.user)
        self.assertEqual(project.domain.name, payload["dataDomain"])
        self.assertEqual(project.intake_metadata.get("dashboard"), payload["dashboard"])
        self.assertEqual(project.intake_metadata.get("objective"), payload["objective"])
        self.assertEqual(DataDomain.objects.filter(tenant=self.tenant, name=payload["dataDomain"]).count(), 1)

    def test_create_project_with_same_name_returns_conflict(self):
        domain = DataDomain.objects.create(
            tenant=self.tenant,
            name="Controladoria e Risco",
            owner=self.user,
        )
        Project.objects.create(
            tenant=self.tenant,
            domain=domain,
            name="Dashboard Unico",
            created_by=self.user,
        )

        response = self.client.post(
            "/api/v1/projects/projects/",
            {
                "dashboard": "Dashboard Unico",
                "dataDomain": "Controladoria e Risco",
                "domainDataOwner": "owner@empresa.com",
                "confidentiality": "Uso Interno Geral",
                "crawlFrequency": "Batch Diario",
                "objective": "Teste de conflito.",
            },
            format="json",
            **self.tenant_headers,
        )

        self.assertEqual(response.status_code, 409, response.data)
        self.assertIn("detail", response.data)
