from unittest.mock import patch

from django.test import override_settings
from django.test import SimpleTestCase

from apps.ai_engine.services.incremental_dashboard_agent import IncrementalDashboardAgentService
from apps.ai_engine.services.nl2sql_service import NL2SQLService


class NL2SQLServiceTests(SimpleTestCase):
    def setUp(self):
        self.service = NL2SQLService()

    def test_build_sql_proposal_prefers_semantic_join_when_available(self):
        datasets = [
            {
                "id": "1",
                "name": "Pedidos",
                "sqlite_table": "pedidos_1",
                "schema_json": {
                    "columns": [
                        {"name": "customer id", "type": "TEXT"},
                    ]
                },
            },
            {
                "id": "2",
                "name": "Clientes",
                "sqlite_table": "clientes_2",
                "schema_json": {
                    "columns": [
                        {"name": "id", "type": "TEXT"},
                    ]
                },
            },
        ]
        semantic_relationships = [
            {
                "source": "Pedidos",
                "target": "Clientes",
                "sourceKey": "customer id",
                "targetKey": "id",
                "type": "Left",
            }
        ]

        proposal = self.service.build_sql_proposal(datasets, semantic_relationships)

        self.assertIn("LEFT JOIN", proposal["sql"])
        self.assertIn('s."customer_id" = t."id"', proposal["sql"])

    def test_build_sql_proposal_uses_grouped_distribution_when_dimension_exists(self):
        datasets = [
            {
                "id": "1",
                "name": "Vendas",
                "sqlite_table": "vendas_1",
                "selectedCols": ["Region"],
                "schema_json": {
                    "columns": [
                        {"name": "Region", "type": "TEXT"},
                        {"name": "Revenue", "type": "REAL"},
                    ]
                },
            }
        ]

        proposal = self.service.build_sql_proposal(datasets, semantic_relationships=[])

        self.assertIn('GROUP BY "region"', proposal["sql"])
        self.assertIn('ORDER BY total_registros DESC', proposal["sql"])

    def test_build_sql_proposal_falls_back_to_count_without_metadata(self):
        datasets = [{"id": "1", "name": "Base", "sqlite_table": "base_1", "schema_json": {}}]

        proposal = self.service.build_sql_proposal(datasets, semantic_relationships=[])

        self.assertEqual(proposal["sql"], 'SELECT COUNT(*) AS total_registros FROM "base_1";')

    def test_build_sql_proposal_does_not_infer_columns_from_sample_without_schema_or_selection(self):
        datasets = [
            {
                "id": "1",
                "name": "Base",
                "sqlite_table": "base_1",
                "schema_json": {},
                "sample_json": [{"categoria": "A"}, {"categoria": "B"}],
            }
        ]

        proposal = self.service.build_sql_proposal(datasets, semantic_relationships=[])

        self.assertEqual(proposal["sql"], 'SELECT COUNT(*) AS total_registros FROM "base_1";')

    def test_build_sql_proposal_requires_explicit_table_identifier(self):
        datasets = [
            {
                "id": "1",
                "name": "somente_nome_sem_sqlite_table",
                "schema_json": {
                    "columns": [{"name": "region", "type": "TEXT"}],
                },
            }
        ]

        proposal = self.service.build_sql_proposal(datasets, semantic_relationships=[])

        self.assertIn("Insufficient dataset metadata", proposal["sql"])


class IncrementalContractCompatibilityTests(SimpleTestCase):
    def setUp(self):
        self.service = IncrementalDashboardAgentService()
        self.context = {
            "dashboard": None,
            "project": None,
            "dashboardName": "Demo",
            "reportTitle": "Demo",
            "reportDescription": "Teste",
            "dataDomain": "",
            "domainDataOwner": "",
            "dataConfidentiality": "",
            "crawlerFrequency": "",
            "sessionAuthor": "tester",
            "currentVersion": "v1",
            "currentDashboardState": "DRAFT",
            "previousUserPrompts": ["p1"],
            "currentUserPrompt": "p2",
            "templatePrompt": "",
            "masterPrompt": "",
            "reportMetadata": {},
            "datasets": [],
            "semanticRelationships": [],
            "existingDashboardHtml": "",
            "frontendComponentContract": {},
            "visualLayoutRules": {},
            "outputFormatRules": {},
        }

    def test_normalize_response_accepts_legacy_payload(self):
        legacy_payload = {
            "analysisIntent": {"goal": "x", "contextFusionSummary": "y"},
            "existingAnalysis": {
                "whatAlreadyExists": "a",
                "whatWillBeKept": "b",
                "whatWillBeChanged": "c",
                "whatWillBeAdded": "d",
            },
            "governanceContext": {"dataDomain": "d", "dataOwner": "o", "confidentiality": "i"},
            "sqlProposal": {"description": "desc", "sql": "/* noop */"},
            "dashboardPlan": {"structure": ["cabecalho"], "changesFromPreviousVersion": ["delta"]},
            "htmlDashboard": "<html></html>",
            "footerInsights": ["i1"],
            "versionAction": {"type": "wrong_value", "reason": "r"},
            "limitations": ["l1"],
        }

        result = self.service._normalize_response(legacy_payload, self.context)

        self.assertIn("applicationAnalysis", result)
        self.assertIn("architecturePlan", result)
        self.assertIn("existingAnalysis", result)
        self.assertEqual(result["versionAction"]["type"], "save_draft")


class IncrementalBedrockActivationTests(SimpleTestCase):
    def setUp(self):
        self.service = IncrementalDashboardAgentService()

    @override_settings(
        USE_BEDROCK_LLM=True,
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3"}},
        AWS_ACCESS_KEY_ID="",
        AWS_SECRET_ACCESS_KEY="",
        BEDROCK_REGION="us-east-1",
    )
    def test_should_not_try_bedrock_in_sqlite_without_credentials(self):
        self.assertFalse(self.service._should_try_bedrock())

    @override_settings(
        USE_BEDROCK_LLM=True,
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3"}},
        AWS_ACCESS_KEY_ID="key",
        AWS_SECRET_ACCESS_KEY="secret",
        BEDROCK_REGION="us-east-1",
    )
    def test_should_try_bedrock_in_sqlite_with_credentials(self):
        self.assertTrue(self.service._should_try_bedrock())

    @override_settings(
        USE_BEDROCK_LLM=False,
        DATABASES={"default": {"ENGINE": "django.db.backends.postgresql"}},
        BEDROCK_REGION="us-east-1",
    )
    def test_should_not_try_bedrock_when_flag_is_disabled(self):
        self.assertFalse(self.service._should_try_bedrock())

    @override_settings(
        USE_BEDROCK_LLM=True,
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3"}},
        AWS_ACCESS_KEY_ID="key",
        AWS_SECRET_ACCESS_KEY="secret",
        BEDROCK_REGION="us-east-1",
        BEDROCK_KB_ID="kb-123",
        BEDROCK_KB_MAX_RESULTS=3,
    )
    def test_build_context_includes_kb_retrieved_snippets(self):
        with patch.object(self.service, "_bedrock_client") as bedrock_client:
            bedrock_client.return_value.retrieve_kb_context.return_value = [
                {"text": "Contexto 1", "score": 0.9, "source": "s3://bucket/doc1"},
                {"text": "Contexto 2", "score": 0.8, "source": "s3://bucket/doc2"},
            ]
            context = self.service._build_context(
                {
                    "currentUserPrompt": "mostrar crescimento por regiao",
                    "previousUserPrompts": ["analise inicial"],
                    "reportTitle": "Receita Mensal",
                    "reportDescription": "Dash de receita",
                    "knowledgeBasePromptHints": ["template html corporativo", "paleta institucional"],
                    "datasets": [],
                    "semanticRelationships": [],
                }
            )

        self.assertIn("ragRetrievedContext", context)
        self.assertIn("knowledgeBasePromptHints", context)
        self.assertEqual(len(context["knowledgeBasePromptHints"]), 2)
        self.assertEqual(len(context["ragRetrievedContext"]), 2)
        self.assertEqual(context["ragRetrievedContext"][0]["text"], "Contexto 1")

    def test_ensure_operational_output_enforces_fetch_html_and_six_insights(self):
        result = {
            "sqlProposal": {"sql": 'SELECT COUNT(*) AS total FROM "vendas_demo";'},
            "htmlDashboard": "<html><body>nao operacional</body></html>",
            "footerInsights": ["insight unico"],
            "limitations": [],
        }
        context = {
            "reportTitle": "Demo",
            "reportDescription": "Teste",
            "datasets": [
                {
                    "id": "dataset-1",
                    "name": "vendas_demo",
                    "sqlite_table": "vendas_demo",
                    "schema_json": {"columns": [{"name": "regiao", "type": "TEXT"}]},
                    "sample_json": [{"regiao": "Norte"}],
                }
            ],
            "semanticRelationships": [],
            "knowledgeBasePromptHints": [],
            "currentUserPrompt": "quero analise operacional",
            "reportMetadata": {"apiBaseUrl": "http://127.0.0.1:8000"},
        }

        self.service._ensure_operational_output(result, context)

        self.assertIn("/api/v1/copilot/sql-preview", result["htmlDashboard"])
        self.assertIn("fetch(", result["htmlDashboard"])
        self.assertEqual(len(result["footerInsights"]), 6)
