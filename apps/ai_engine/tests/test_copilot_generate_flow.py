import uuid
from unittest.mock import MagicMock

from django.test import SimpleTestCase, override_settings
from rest_framework.test import APITestCase

from apps.ai_engine.services.incremental_dashboard_agent import IncrementalDashboardAgentService


class CopilotGenerateFlowAPITests(APITestCase):
    def _build_frontend_like_payload(self) -> dict:
        return {
            "dashboard_id": None,
            "project_id": str(uuid.uuid4()),
            "dashboardName": "Dashboard Corporativo",
            "reportTitle": "Dashboard Corporativo",
            "reportDescription": "Evolucao incremental do dashboard corporativo.",
            "dataDomain": "Comercial",
            "domainDataOwner": "owner@empresa.com",
            "dataConfidentiality": "INTERNAL",
            "crawlerFrequency": "daily",
            "sessionAuthor": "frontend-local",
            "currentVersion": "v2.0 (Rascunho)",
            "currentDashboardState": "DRAFT",
            "previousUserPrompts": [
                "Quero uma visao executiva de receita por regiao.",
                "Adicione comparativo mensal e destaque anomalias.",
            ],
            "currentUserPrompt": "Agora foque em rentabilidade por segmento e canal.",
            "templatePrompt": "",
            "masterPrompt": "",
            "reportMetadata": {
                "activeTabId": "v2.0",
                "tabsCount": 2,
                "apiBaseUrl": "http://127.0.0.1:8000",
            },
            "datasets": [
                {
                    "id": "dataset-1",
                    "name": "vendas_abril",
                    "source_type": "CSV",
                    "sqlite_table": "vendas_abril",
                    "row_count": 1500,
                    "column_count": 5,
                    "schema_json": {
                        "columns": [
                            {"name": "regiao", "type": "TEXT"},
                            {"name": "segmento", "type": "TEXT"},
                            {"name": "canal", "type": "TEXT"},
                            {"name": "receita", "type": "REAL"},
                            {"name": "custo", "type": "REAL"},
                        ]
                    },
                    "sample_json": [
                        {
                            "regiao": "Norte",
                            "segmento": "PME",
                            "canal": "Online",
                            "receita": 1000,
                            "custo": 650,
                        },
                        {
                            "regiao": "Sul",
                            "segmento": "Enterprise",
                            "canal": "Parceiros",
                            "receita": 2100,
                            "custo": 1200,
                        },
                    ],
                    "selectedCols": ["regiao", "segmento", "canal", "receita", "custo"],
                }
            ],
            "semanticRelationships": [],
            "knowledgeBasePromptHints": [
                "template html padrao corporativo",
                "layout executivo institucional",
                "paleta de cores corporativa",
            ],
            "existingDashboardHtml": "<html><body><h1>Versao anterior</h1></body></html>",
            "frontendComponentContract": {
                "expectsStandaloneHtml": True,
                "renderMode": "iframe-srcdoc",
            },
            "visualLayoutRules": {
                "style": "executive-corporate",
                "preserveExistingStructure": True,
            },
            "outputFormatRules": {
                "requireValidJson": True,
                "preserveDraftFlow": True,
            },
            "query": "Agora foque em rentabilidade por segmento e canal.",
        }

    @override_settings(
        USE_BEDROCK_LLM=False,
        USE_AWS_DATA_SERVICES=False,
    )
    def test_generate_endpoint_returns_complete_operational_dashboard_html(self):
        payload = self._build_frontend_like_payload()
        response = self.client.post("/api/v1/copilot/generate", payload, format="json")

        self.assertEqual(response.status_code, 200, response.data)
        body = response.data

        required_fields = [
            "applicationAnalysis",
            "architecturePlan",
            "analysisIntent",
            "sqlProposal",
            "dashboardPlan",
            "htmlDashboard",
            "footerInsights",
            "versionAction",
            "limitations",
            "sqlValidation",
            "dashboard_html",
            "sql",
            "insights",
            "generationMetadata",
        ]
        for field in required_fields:
            self.assertIn(field, body)

        html = body["htmlDashboard"]
        self.assertIsInstance(html, str)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("/api/v1/copilot/sql-preview", html)
        self.assertIn("fetch(", html)
        self.assertIn('data-agent-bi-operational-dashboard="true"', html)
        self.assertEqual(body["dashboard_html"], html)

        self.assertEqual(body["versionAction"]["type"], "save_draft")
        self.assertEqual(len(body["footerInsights"]), 6)
        self.assertEqual(body["insights"], body["footerInsights"])

        self.assertIn("sql", body["sqlProposal"])
        self.assertTrue(body["sqlProposal"]["sql"])
        self.assertEqual(body["sql"], body["sqlProposal"]["sql"])
        self.assertEqual(body["sqlValidation"]["status"], "validated")
        self.assertIn(
            body["sqlValidation"]["engine"],
            {"sqlite-local-inmemory-fallback", "sqlite-analytics-local"},
        )
        self.assertEqual(body["generationMetadata"]["responseSource"], "local_fallback")
        self.assertFalse(body["generationMetadata"]["strictBedrock"])

    @override_settings(
        USE_BEDROCK_LLM=False,
        USE_AWS_DATA_SERVICES=False,
    )
    def test_generate_endpoint_rejects_when_strict_bedrock_is_required_but_unavailable(self):
        payload = self._build_frontend_like_payload()
        payload["requireBedrock"] = True

        response = self.client.post("/api/v1/copilot/generate", payload, format="json")

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("Bedrock", str(response.data.get("detail", "")))


class IncrementalPromptSubmissionTests(SimpleTestCase):
    @override_settings(
        USE_BEDROCK_LLM=True,
        BEDROCK_REGION="us-east-1",
        DATABASES={"default": {"ENGINE": "django.db.backends.postgresql"}},
    )
    def test_service_submits_fused_frontend_context_to_llm(self):
        service = IncrementalDashboardAgentService()
        mock_bedrock = MagicMock()
        mock_bedrock.last_invoke_metadata = {
            "provider": "bedrock",
            "response_origin": "model_runtime",
            "success": True,
        }
        mock_bedrock.invoke_with_json_output.return_value = {
            "applicationAnalysis": {
                "existingModules": "ok",
                "capabilitiesIdentified": "ok",
                "gaps": "ok",
            },
            "architecturePlan": {
                "planner": "ok",
                "nl2sql": "ok",
                "htmlRenderer": "ok",
            },
            "analysisIntent": {
                "goal": "ok",
                "contextFusionSummary": "ok",
                "evolutionStrategy": "ok",
            },
            "sqlProposal": {
                "description": "ok",
                "sql": 'SELECT COUNT(*) AS total FROM "vendas_demo";',
            },
            "dashboardPlan": {
                "structure": ["cabecalho executivo"],
                "components": [{"type": "header"}],
                "changesFromPreviousVersion": ["ajuste incremental"],
            },
            "htmlDashboard": "<html><body>nao operacional</body></html>",
            "footerInsights": ["insight-1"],
            "versionAction": {"type": "save_draft", "reason": "ok"},
            "limitations": [],
        }
        service._bedrock_client = lambda: mock_bedrock

        payload = {
            "dashboardName": "Painel Comercial",
            "reportTitle": "Painel Comercial",
            "reportDescription": "Analise executiva de receita e margem.",
            "templatePrompt": "template corporativo",
            "masterPrompt": "politicas enterprise",
            "previousUserPrompts": ["baseline inicial"],
            "currentUserPrompt": "adicionar leitura por canal",
            "knowledgeBasePromptHints": ["layout executivo institucional"],
            "datasets": [
                {
                    "id": "dataset-1",
                    "name": "vendas_demo",
                    "sqlite_table": "vendas_demo",
                    "schema_json": {
                        "columns": [
                            {"name": "canal", "type": "TEXT"},
                            {"name": "receita", "type": "REAL"},
                        ]
                    },
                    "sample_json": [
                        {"canal": "Online", "receita": 100},
                        {"canal": "Loja", "receita": 140},
                    ],
                    "selectedCols": ["canal", "receita"],
                }
            ],
            "semanticRelationships": [],
            "reportMetadata": {"apiBaseUrl": "http://127.0.0.1:8000"},
        }

        result = service.generate(payload, save_version=False)

        mock_bedrock.invoke_with_json_output.assert_called_once()
        kwargs = mock_bedrock.invoke_with_json_output.call_args.kwargs
        user_message = kwargs["user_message"]

        self.assertIn("Evolua incrementalmente o dashboard", user_message)
        self.assertIn('"templatePrompt": "template corporativo"', user_message)
        self.assertIn('"masterPrompt": "politicas enterprise"', user_message)
        self.assertIn('"currentUserPrompt": "adicionar leitura por canal"', user_message)
        self.assertIn('"knowledgeBasePromptHints"', user_message)
        self.assertIn('"datasets"', user_message)

        self.assertIn("/api/v1/copilot/sql-preview", result["htmlDashboard"])
        self.assertIn("fetch(", result["htmlDashboard"])
        self.assertEqual(result["dashboard_html"], result["htmlDashboard"])
        self.assertEqual(result["generationMetadata"]["responseSource"], "bedrock")
        self.assertTrue(result["generationMetadata"]["bedrockUsed"])
