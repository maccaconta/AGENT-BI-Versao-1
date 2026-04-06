from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from apps.ai_engine.services.html_renderer_service import DashboardHtmlRendererService


class CopilotSQLPreviewAPITests(APITestCase):
    def test_sql_preview_executes_read_only_query(self):
        payload = {
            "sql": 'SELECT "regiao", COUNT(*) AS total FROM "vendas_demo" GROUP BY "regiao" ORDER BY total DESC;',
            "datasets": [
                {
                    "id": "dataset-1",
                    "name": "vendas_demo",
                    "sqlite_table": "vendas_demo",
                    "schema_json": {
                        "columns": [
                            {"name": "regiao", "type": "TEXT"},
                            {"name": "receita", "type": "REAL"},
                        ]
                    },
                    "sample_json": [
                        {"regiao": "Norte", "receita": 100},
                        {"regiao": "Sul", "receita": 200},
                        {"regiao": "Norte", "receita": 150},
                    ],
                }
            ],
            "limit": 50,
        }

        response = self.client.post("/api/v1/copilot/sql-preview", payload, format="json")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("rows", response.data)
        self.assertIn("columns", response.data)
        self.assertIn("engine", response.data)

    def test_sql_preview_blocks_non_read_only_query(self):
        payload = {
            "sql": 'DELETE FROM "vendas_demo";',
            "datasets": [
                {
                    "id": "dataset-1",
                    "name": "vendas_demo",
                    "sqlite_table": "vendas_demo",
                    "schema_json": {"columns": [{"name": "regiao", "type": "TEXT"}]},
                    "sample_json": [{"regiao": "Norte"}],
                }
            ],
        }

        response = self.client.post("/api/v1/copilot/sql-preview", payload, format="json")

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("detail", response.data)


class DashboardHtmlRendererOperationalTests(SimpleTestCase):
    def test_renderer_builds_operational_dashboard_html_with_fetch_markers(self):
        renderer = DashboardHtmlRendererService()
        context = {
            "reportTitle": "Teste Operacional",
            "reportDescription": "Descricao teste",
            "datasets": [
                {
                    "id": "dataset-1",
                    "name": "vendas_demo",
                    "sqlite_table": "vendas_demo",
                    "schema_json": {"columns": [{"name": "regiao", "type": "TEXT"}]},
                    "sample_json": [{"regiao": "Norte"}],
                }
            ],
            "reportMetadata": {"apiBaseUrl": "http://127.0.0.1:8000"},
        }
        html = renderer.build_operational_html(
            context=context,
            footer_insights=["i1"],
            sql_proposal={"sql": 'SELECT COUNT(*) AS total FROM "vendas_demo";'},
        )

        self.assertIn('data-agent-bi-operational-dashboard="true"', html)
        self.assertIn("/api/v1/copilot/sql-preview", html)
        self.assertIn("fetch(", html)
        self.assertTrue(renderer.is_operational_dashboard_html(html))
