"""
apps.ai_engine.agents.generator_agent
Generator Agent legado: gera SQL + HTML via IA.
"""
from __future__ import annotations

import logging
import time

from django.conf import settings

from apps.ai_engine.prompts.generator_prompt import (
    GENERATOR_SYSTEM_PROMPT,
    build_generator_prompt,
)
from apps.ai_engine.services.bedrock_service import BedrockInvocationError, BedrockService
from apps.datasets.services.athena_service import AthenaQueryError, AthenaService

logger = logging.getLogger(__name__)


class GeneratorAgentError(Exception):
    """Erro no Generator Agent."""


class GeneratorAgentResult:
    """Resultado estruturado do Generator Agent."""

    def __init__(self, data: dict):
        self.sql_queries: list = data.get("sql_queries", [])
        self.insights: str = data.get("insights", "")
        self.html: str = data.get("html", "")
        self.query_results: list = []
        self.execution_time_seconds: float = 0.0
        self.raw_response: dict = data

    @property
    def is_valid(self) -> bool:
        return bool(self.html) and bool(self.sql_queries)


class GeneratorAgent:
    """
    Agent legado responsavel por:
    1. Gerar SQL analitico
    2. Executar queries (Athena quando habilitado)
    3. Gerar dashboard HTML

    No modo local demo (`USE_AWS_DATA_SERVICES=False`), nao executa Athena.
    """

    def __init__(self):
        self.use_aws_data_services = bool(getattr(settings, "USE_AWS_DATA_SERVICES", True))
        self.bedrock = BedrockService()
        self.athena = AthenaService() if self.use_aws_data_services else None

    def generate(
        self,
        instruction: str,
        dataset,
        template_hints: str = "",
        previous_feedback: str = "",
        iteration: int = 1,
    ) -> GeneratorAgentResult:
        start_time = time.time()
        logger.info(
            "Generator Agent: iniciando geracao. Instrucao='%s...' iteracao=%s",
            instruction[:100],
            iteration,
        )

        schema = dataset.schema_json or {}
        sample_data = self._get_sample_data(dataset)

        prompt = build_generator_prompt(
            instruction=instruction,
            schema=schema,
            sample_data=sample_data,
            dataset_name=dataset.name,
            database=dataset.glue_database,
            table=dataset.glue_table,
            template_hints=template_hints,
            previous_feedback=previous_feedback,
            iteration=iteration,
        )

        from apps.governance.models import GlobalSystemPrompt

        tenant = dataset.project.tenant
        global_policy = GlobalSystemPrompt.objects.filter(tenant=tenant, is_active=True).first()
        system_instructions = GENERATOR_SYSTEM_PROMPT
        if global_policy:
            system_instructions = global_policy.generate_full_system_prompt() + "\n\n" + GENERATOR_SYSTEM_PROMPT

        try:
            response_data = self.bedrock.invoke_with_json_output(
                system_prompt=system_instructions,
                user_message=prompt,
                temperature=0.3 if iteration == 1 else 0.4,
            )
        except BedrockInvocationError as exc:
            raise GeneratorAgentError(f"Erro ao invocar Bedrock: {exc}") from exc

        result = GeneratorAgentResult(response_data)
        if not result.sql_queries:
            raise GeneratorAgentError("Generator nao retornou queries SQL.")
        if not result.html:
            raise GeneratorAgentError("Generator nao retornou HTML do dashboard.")

        query_results = []
        if self.use_aws_data_services and dataset.glue_database:
            query_results = self._execute_queries(result.sql_queries, dataset.glue_database)
            result.query_results = query_results
            if query_results:
                result.html = self._inject_real_data(
                    html=result.html,
                    sql_queries=result.sql_queries,
                    query_results=query_results,
                    dataset_id=str(dataset.id),
                )

        result.execution_time_seconds = time.time() - start_time
        logger.info("Generator Agent: concluido em %.2fs", result.execution_time_seconds)
        return result

    def _get_sample_data(self, dataset) -> dict:
        """Obtem amostra via Athena (AWS) ou snapshot local do dataset (demo)."""
        if not self.use_aws_data_services:
            sample_rows = dataset.sample_json[:10] if isinstance(dataset.sample_json, list) else []
            columns = list(sample_rows[0].keys()) if sample_rows and isinstance(sample_rows[0], dict) else []
            return {"columns": columns, "rows": sample_rows, "row_count": len(sample_rows)}

        try:
            if not dataset.glue_database or not dataset.glue_table:
                return {}
            result = self.athena.get_sample_data(
                database=dataset.glue_database,
                table=dataset.glue_table,
                limit=10,
            )
            return result.get("results", {})
        except AthenaQueryError as exc:
            logger.warning("Nao foi possivel obter amostra de dados: %s", exc)
            return {}

    def _execute_queries(self, sql_queries: list, database: str) -> list:
        """Executa as queries SQL no Athena quando habilitado."""
        if not self.use_aws_data_services:
            return []

        results = []
        for query_spec in sql_queries:
            sql = query_spec.get("sql", "")
            if not sql:
                results.append(None)
                continue

            try:
                result = self.athena.execute_query(sql=sql, database=database, wait=True)
                results.append(result.get("results", {}))
                logger.info(
                    "Query '%s' executada. Linhas: %s",
                    query_spec.get("name", "unknown"),
                    result.get("results", {}).get("row_count", 0),
                )
            except AthenaQueryError as exc:
                logger.error("Erro ao executar query: %s", exc)
                results.append({"error": str(exc), "columns": [], "rows": []})

        return results

    def _inject_real_data(
        self,
        html: str,
        sql_queries: list,
        query_results: list,
        dataset_id: str = "",
    ) -> str:
        """
        Injeta dados de contexto no HTML.
        """
        if not sql_queries:
            return html

        main_sql = sql_queries[0].get("sql", "")
        main_sql_escaped = main_sql.replace("`", r"\`").replace("'", r"\'").replace('"', r"\"")
        script_tag = f"""
            <script>
                // Injetado pelo Agent-BI Backend
                window.AGENT_BI_DATASET_ID = '{dataset_id}';
                window.AGENT_BI_SQL = "{main_sql_escaped}";
            </script>
            """
        if "</head>" in html:
            return html.replace("</head>", f"{script_tag}\n</head>")
        return f"{script_tag}\n{html}"

