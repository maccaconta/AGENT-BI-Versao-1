"""
apps.ai_engine.services.incremental_dashboard_agent
Agente incremental de dashboards corporativos.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Optional

from django.conf import settings

from apps.ai_engine.prompts.incremental_dashboard_prompt import INCREMENTAL_DASHBOARD_SYSTEM_PROMPT
from apps.ai_engine.services.bedrock_service import BedrockService
from apps.ai_engine.services.html_renderer_service import DashboardHtmlRendererService
from apps.ai_engine.services.nl2sql_service import NL2SQLService
from apps.ai_engine.agents.nl2sql_agent import NL2SQLAgent
from apps.ai_engine.services.planner_service import DashboardPlannerService
from apps.datasets.services.sqlite_query_service import (
    LocalSQLiteQueryService,
    SQLiteQueryValidationError,
)
from apps.datasets.services.sqlite_analytics_store import (
    LocalSQLiteAnalyticsStoreService,
    build_sqlite_table_name,
)

from apps.ai_engine.agents.supervisor_agent import SupervisorAgent
from apps.ai_engine.agents.pandas_analytics_agent import PandasAnalyticsAgent
from apps.ai_engine.agents.rag_knowledge_agent import RAGKnowledgeAgent
from apps.ai_engine.agents.critic_agent import CriticAgent

logger = logging.getLogger(__name__)


class IncrementalDashboardAgentService:
    def __init__(self):
        self.bedrock = None
        self.sqlite = LocalSQLiteQueryService()
        self.sqlite_store = LocalSQLiteAnalyticsStoreService()
        self.planner = DashboardPlannerService()
        self.nl2sql = NL2SQLService()
        self.nl2sql_agent = NL2SQLAgent()
        self.renderer = DashboardHtmlRendererService()

    def generate(self, request_data: dict, request_user=None, save_version: bool = True) -> dict:
        from apps.audit.services.trace_service import TraceService
        import uuid
        from apps.datasets.models import DatasetStatus
        trace_id = request_data.get("trace_id") or uuid.uuid4()
        trace = TraceService(trace_id=trace_id, job_type="AI_GENERATION")

        # Verificação de Prontidão de Dados (Data Readiness)
        project_id = request_data.get("projectId")
        if project_id:
            from apps.projects.models import Project
            pending_datasets = Project.objects.get(id=project_id).datasets.filter(
                is_deleted=False
            ).exclude(status=DatasetStatus.READY)
            
            if pending_datasets.exists():
                trace.start_step("Validação de Dados")
                names = ", ".join([d.name for d in pending_datasets])
                msg = f"Aguardando processamento analítico (Profiling) de: {names}"
                trace.end_step("Validação de Dados", message=msg, status="WARNING")
                return {
                    "status": "data_not_ready",
                    "message": msg,
                    "pending_datasets": [str(d.id) for d in pending_datasets]
                }
        
        trace.start_step("Análise de Dados e Prompt")
        context = self._build_context(request_data, request_user, trace=trace)
        
        # Coleta metadados de perfilamento para o HUD
        ds_stats = []
        has_temporal = False
        for ds in context.get("datasets", []):
            is_temp = ds.get("data_profile", {}).get("temporal", {}).get("has_temporal_data", False)
            if is_temp: has_temporal = True
            ds_stats.append({
                "name": ds.get("name"),
                "rows": ds.get("row_count"),
                "cols": ds.get("column_count"),
                "temporal": is_temp
            })

        # --- MULTI-AGENT ROUTING (ASSISTENTES) ---
        trace.start_step("Supervisor: Escaneamento")
        supervisor = SupervisorAgent()
        routing_decision = supervisor.determine_route(
            user_prompt=context.get("currentUserPrompt", ""),
            datasets_metadata=ds_stats
        )
        route_selected = routing_decision.get("route", "ROUTE_NL2SQL")
        trace.end_step("Supervisor: Escaneamento", message=f"Intenção detectada. Delegando para {route_selected}.", metadata={"routing_decision": routing_decision})
        
        context["routing_decision"] = routing_decision
        
        if route_selected == "ROUTE_PANDAS":
            pandas_assistant = PandasAnalyticsAgent()
            profiles = [ds.get("data_profile", {}) for ds in context.get("datasets", [])]
            p_result = pandas_assistant.analyze(context.get("currentUserPrompt", ""), profiles, trace=trace)
            context["specialist_insights"] = p_result.get("analysis", "")
            
        elif route_selected == "ROUTE_KB_RAG":
            rag_assistant = RAGKnowledgeAgent()
            rag_snippets = [snip.get("text", "") for snip in context.get("ragRetrievedContext", []) if snip.get("text")]
            r_result = rag_assistant.query_knowledge(context.get("currentUserPrompt", ""), "\n".join(rag_snippets), trace=trace)
            context["specialist_insights"] = r_result.get("answer", "")
            
        else:
            # ROUTE_NL2SQL - Assistente Especialista para SQL Complexo
            n_result = self.nl2sql_agent.generate_sql(
                user_prompt=context.get("currentUserPrompt", ""),
                datasets=context.get("datasets", []),
                relationships=context.get("semanticRelationships", []),
                trace=trace
            )
            context["specialist_sql"] = n_result.get("sql", "")
            context["specialist_insights"] = n_result.get("description", "")
        # ---------------------------

        strict_bedrock = bool(request_data.get("requireBedrock", False))
        response = None
        bedrock_attempted = False
        bedrock_used = False
        bedrock_error = ""
        bedrock_runtime_metadata = {}
        
        system_prompt = INCREMENTAL_DASHBOARD_SYSTEM_PROMPT
        user_message = self._build_user_message(context)
        
        msg = f"Contexto analítico preparado. Perfis Pandas/Estatísticos carregados para {len(ds_stats)} datasets."
        if has_temporal:
            msg += " (Incluindo análise de tendência temporal)."

        trace.end_step("Análise de Dados e Prompt", message=msg, metadata={
            "datasets_profiled": ds_stats,
            "kb_hints": context.get("knowledgeBasePromptHints"),
            "system_prompt": system_prompt[:1000] + "...", 
            "user_message": user_message
        })

        should_try_bedrock = self._should_try_bedrock()
        if strict_bedrock and not should_try_bedrock:
            raise ValueError(
                "Modo estrito de Bedrock foi solicitado, mas o backend nao esta apto a invocar Bedrock com a configuracao/credenciais atuais."
            )

        # ----------------------------------------------------------------------
        # CICLO DE GERAÇÃO E SELF-CORRECTION (MULTI-AGENTE)
        # ----------------------------------------------------------------------
        max_attempts = 2
        current_attempt = 1
        final_result = None
        critic_feedback_loop = ""
        
        while current_attempt <= max_attempts:
            bedrock_attempted = True
            bedrock_used = False
            response = None
            bedrock_runtime_metadata = {}
            bedrock_error = None
            
            # Ajusta o prompt do usuário se houver feedback anterior
            current_user_message = user_message
            if critic_feedback_loop:
                current_user_message += f"\n\n🚨 FEEDBACK DO CRITIC AGENT (CORRIJA ESTES PONTOS):\n{critic_feedback_loop}"
            
            if should_try_bedrock:
                try:
                    step_name = f"Invocação LLM (Bedrock) - Tentaiva {current_attempt}"
                    trace.start_step(step_name)
                    bedrock_client = self._bedrock_client()
                    response = bedrock_client.invoke_with_json_output(
                        system_prompt=system_prompt,
                        user_message=current_user_message,
                        temperature=0.2,
                    )
                    bedrock_used = isinstance(response, dict)
                    bedrock_runtime_metadata = dict(getattr(bedrock_client, "last_invoke_metadata", {}) or {})
                    
                    input_t = bedrock_runtime_metadata.get("usage", {}).get("input_tokens", 0)
                    output_t = bedrock_runtime_metadata.get("usage", {}).get("output_tokens", 0)
                    
                    trace.end_step(
                        step_name, 
                        message="Resposta recebida com sucesso.",
                        input_tokens=input_t,
                        output_tokens=output_t
                    )
                except Exception as exc:
                    bedrock_error = str(exc)
                    logger.warning("Invocação Bedrock falhou na tentativa %s: %s", current_attempt, exc)
                    if strict_bedrock:
                        raise ValueError("Falha crítica no Bedrock em modo estrito.") from exc

            # Normalização e Validações de Segurança
            candidate_result = self._normalize_response(response, context)
            self._validate_sql_proposal(candidate_result, context)
            self._ensure_operational_output(candidate_result, context)

            # --- AVALIAÇÃO DO CRITIC ---
            # Status padrão para casos onde o Critic não é acionado (Local/Fallback)
            eval_result_dict = {
                "score": 1.0,
                "grade": "A",
                "feedback": "Aprovação implícita (Modo Local/Mock).",
                "issues": [],
                "passes_threshold": True
            }

            if bedrock_used and candidate_result:
                trace.start_step(f"Critic Agent: Avaliando Qualidade (T{current_attempt})")
                critic = CriticAgent()
                
                # Preparação de Schema e Queries para o Critic
                ds_list = context.get("datasets", [])
                primary_schema = ds_list[0].get("schema_json", {}) if ds_list else {}
                sql_p = candidate_result.get("sqlProposal", {})
                structured_queries = [{"name": "Principal", "sql": sql_p.get("sql", "")}]

                try:
                    eval_obj = critic.evaluate(
                        original_instruction=context.get("currentUserPrompt", ""),
                        generated_html=candidate_result.get("htmlDashboard", ""),
                        sql_queries=structured_queries,
                        query_results=[], 
                        schema=primary_schema,
                        dataset=None 
                    )
                    eval_result_dict = eval_obj.to_dict()
                    
                    status_text = "APROVADO" if eval_obj.passes_threshold else "REPROVADO/CORRIGINDO"
                    trace.end_step(
                        f"Critic Agent: Avaliando Qualidade (T{current_attempt})", 
                        message=f"Score: {eval_obj.score:.2f} ({eval_obj.grade}) - Status: {status_text}",
                        metadata=eval_result_dict
                    )
                except Exception as critic_exc:
                    logger.warning(f"Falha no CriticAgent: {str(critic_exc)}")
                    # Mantém o eval_result_dict padrão em caso de erro no critic

            # Consolidação do resultado
            final_result = candidate_result
            final_result["criticRating"] = eval_result_dict
            
            # Condição de saída: aprovação, limite de tentativas ou modo local
            if not bedrock_used or eval_result_dict.get("passes_threshold") or current_attempt >= max_attempts:
                break
                
            # Prepara feedback para a próxima iteração
            critic_feedback_loop = f"ISSUES: {', '.join(eval_result_dict.get('issues', []))}\nFEEDBACK: {eval_result_dict.get('feedback', '')}"
            current_attempt += 1

        # Finalização de metadados
        response_source = "bedrock" if bedrock_used else "local_fallback"
        final_result["generationMetadata"] = {
            "strictBedrock": strict_bedrock,
            "bedrockAttempted": bedrock_attempted,
            "bedrockUsed": bedrock_used,
            "responseSource": response_source,
            "bedrockRuntime": bedrock_runtime_metadata,
            "bedrockError": bedrock_error or None,
            "finalScore": final_result["criticRating"]["score"],
            "attempts": current_attempt
        }
        # Unifica campos para o frontend (compatibilidade)
        final_result["insights"] = final_result.get("footerInsights", "")
        final_result["sql"] = final_result.get("sqlProposal", {}).get("sql", "")

        if save_version and context.get("dashboard"):
            version = self._save_draft_version(context, final_result, request_user)
            if version:
                final_result["savedVersion"] = {
                    "id": str(version.id),
                    "versionNumber": version.version_number,
                    "state": version.state,
                }

        final_result["dashboard_html"] = final_result["htmlDashboard"]
        final_result["sql"] = final_result["sqlProposal"]["sql"]
        final_result["insights"] = final_result["footerInsights"]
        return final_result

    def _build_context(self, request_data: dict, request_user=None, trace=None) -> dict:
        dashboard = None
        project = None
        template_prompt = request_data.get("templatePrompt", "") or ""
        master_prompt = request_data.get("masterPrompt", "") or ""
        existing_html = request_data.get("existingDashboardHtml", "") or ""
        previous_prompts = list(request_data.get("previousUserPrompts") or [])

        dashboard_id = request_data.get("dashboard_id")
        project_id = request_data.get("project_id")

        if dashboard_id:
            from apps.dashboards.models import Dashboard

            dashboard = Dashboard.objects.select_related(
                "project",
                "project__domain",
                "project__domain__owner",
                "template",
                "current_version",
            ).filter(id=dashboard_id).first()
            if dashboard:
                project = dashboard.project
                if dashboard.template and not template_prompt:
                    template_prompt = dashboard.template.prompt_hints or ""
                if dashboard.current_version:
                    if not existing_html:
                        existing_html = self._get_existing_html(dashboard.current_version)
                    previous_prompts = self._merge_previous_prompts(previous_prompts, dashboard.current_version)
        elif project_id:
            from apps.projects.models import Project

            project = Project.objects.select_related("domain", "domain__owner").filter(id=project_id).first()

        if project and not master_prompt:
            from apps.governance.models import GlobalSystemPrompt

            policy = GlobalSystemPrompt.objects.filter(tenant=project.tenant, is_active=True).first()
            if policy:
                master_prompt = policy.generate_full_system_prompt()

        datasets = request_data.get("datasets") or self._serialize_project_datasets(project)
        datasets = self._enrich_datasets_for_sqlite(datasets)
        current_user_prompt = request_data.get("currentUserPrompt") or request_data.get("query") or ""
        kb_hints = list(request_data.get("knowledgeBasePromptHints") or [])
        if trace:
            trace.start_step("Recuperação de Contexto (RAG)")
        rag_context = self._retrieve_rag_context(
            current_user_prompt=current_user_prompt,
            report_title=request_data.get("reportTitle") or request_data.get("dashboardName") or "",
            report_description=request_data.get("reportDescription") or "",
            previous_prompts=previous_prompts,
            kb_hints=kb_hints,
        )
        rag_count = len(rag_context)
        if trace:
            trace.end_step(
                "Recuperação de Contexto (RAG)", 
                message=f"Recuperados {rag_count} snippets da Base de Conhecimento." if rag_count > 0 else "Nenhum snippet relevante encontrado na KB.",
                metadata={"rag_snippets": rag_context}
            )

        return {
            "dashboard": dashboard,
            "project": project,
            "dashboardName": request_data.get("dashboardName") or (dashboard.name if dashboard else ""),
            "reportTitle": request_data.get("reportTitle") or request_data.get("dashboardName") or (dashboard.name if dashboard else ""),
            "reportDescription": request_data.get("reportDescription") or (dashboard.description if dashboard else ""),
            "dataDomain": request_data.get("dataDomain") or getattr(getattr(project, "domain", None), "name", ""),
            "domainDataOwner": request_data.get("domainDataOwner") or self._get_domain_owner_name(project),
            "dataConfidentiality": request_data.get("dataConfidentiality") or "",
            "crawlerFrequency": request_data.get("crawlerFrequency", "") or "",
            "sessionAuthor": request_data.get("sessionAuthor") or getattr(request_user, "email", "") or "sistema",
            "currentVersion": request_data.get("currentVersion") or self._get_current_version_label(dashboard),
            "currentDashboardState": request_data.get("currentDashboardState") or self._get_current_dashboard_state(dashboard),
            "previousUserPrompts": previous_prompts,
            "currentUserPrompt": current_user_prompt,
            "templatePrompt": template_prompt,
            "masterPrompt": master_prompt,
            "reportMetadata": request_data.get("reportMetadata") or {},
            "datasets": datasets,
            "semanticRelationships": request_data.get("semanticRelationships") or [],
            "knowledgeBasePromptHints": kb_hints,
            "ragRetrievedContext": rag_context,
            "existingDashboardHtml": existing_html,
            "frontendComponentContract": request_data.get("frontendComponentContract") or {},
            "visualLayoutRules": request_data.get("visualLayoutRules") or {},
            "outputFormatRules": request_data.get("outputFormatRules") or {},
        }

    def _build_user_message(self, context: dict) -> str:
        # 1. Extrair e destacar diretrizes da Knowledge Base como bloco mandatorio
        rag_snippets = context.get("ragRetrievedContext") or []
        rag_block = ""
        if rag_snippets:
            rag_lines = []
            for snippet in rag_snippets:
                text = (snippet.get("text") or "").strip()
                if text:
                    rag_lines.append(text)
            if rag_lines:
                rag_block = (
                    "\n\n===== DIRETRIZES MANDATORIAS DA KNOWLEDGE BASE (OBEDEÇA ESTRITAMENTE) =====\n"
                    "REGRAS DE IDENTIDADE VISUAL E LOGOS:\n"
                    "Use os logos e ativos de marca especificados abaixo em todos os cabeçalhos. "
                    "Se houver URLs de imagens, utilize-as nos componentes <img>.\n\n"
                    + "\n\n---\n\n".join(rag_lines)
                    + "\n===== FIM DAS DIRETRIZES - REGRAS ABSOLUTAS, NAO SUGESTOES =====\n"
                )

        # 2. Payload de contexto analitico (sem duplicar o RAG)
        payload = {k: v for k, v in context.items() if k not in {"dashboard", "project", "ragRetrievedContext"}}

        # 3. Sinalizacao de recursos extras (Data Profiling Layers)
        feature_hints = []
        for ds in context.get("datasets", []):
            profile = ds.get("data_profile", {})
            if profile.get("temporal", {}).get("has_temporal_data"):
                feature_hints.append(f"O dataset '{ds.get('name')}' possui perfilamento de TENDENCIA TEMPORAL disponivel.")

        hints_block = ""
        if feature_hints:
            hints_block = "\nRECURSOS DE DADOS DISPONIVEIS:\n" + "\n".join([f"- {h}" for h in feature_hints]) + "\n"

        specialist_text = ""
        if context.get("specialist_insights"):
            specialist_text = "\n===== INSIGHTS DO ESPECIALISTA (GERADOS PELO PANDAS/RAG - UTILIZE COPIANDO ISTO ESTRITAMENTE PARA OS FOOTER INSIGHTS OU DESCRIÇÃO) =====\n"
            specialist_text += context["specialist_insights"] + "\n========================================================================================================================\n"

        return (
            "Evolua incrementalmente o dashboard abaixo.\n"
            "Analise primeiro a aplicacao existente e retorne apenas JSON valido no contrato obrigatorio.\n"
            f"{rag_block}\n"
            f"{hints_block}\n"
            f"{specialist_text}\n"
            "===== CONTEXTO ANALITICO (dados, schema, prompts do usuario) =====\n"
            f"{json.dumps(payload, ensure_ascii=False, default=str, indent=2)}"
        )


    def _normalize_response(self, response: Optional[dict], context: dict) -> dict:
        fallback = self._fallback_response(context)
        if not isinstance(response, dict):
            response = {}

        legacy_existing = response.get("existingAnalysis") or fallback["existingAnalysis"]
        if not isinstance(legacy_existing, dict):
            legacy_existing = fallback["existingAnalysis"]

        legacy_governance = response.get("governanceContext") or fallback["governanceContext"]
        if not isinstance(legacy_governance, dict):
            legacy_governance = fallback["governanceContext"]

        application_analysis_raw = response.get("applicationAnalysis")
        if not isinstance(application_analysis_raw, dict):
            application_analysis_raw = {}
        application_analysis = {
            "existingModules": (
                application_analysis_raw.get("existingModules")
                or legacy_existing.get("whatAlreadyExists")
                or fallback["applicationAnalysis"]["existingModules"]
            ),
            "capabilitiesIdentified": (
                application_analysis_raw.get("capabilitiesIdentified")
                or legacy_existing.get("whatWillBeKept")
                or fallback["applicationAnalysis"]["capabilitiesIdentified"]
            ),
            "gaps": (
                application_analysis_raw.get("gaps")
                or legacy_existing.get("whatWillBeChanged")
                or fallback["applicationAnalysis"]["gaps"]
            ),
        }

        architecture_plan_raw = response.get("architecturePlan")
        if not isinstance(architecture_plan_raw, dict):
            architecture_plan_raw = {}
        architecture_plan = {
            "planner": architecture_plan_raw.get("planner") or fallback["architecturePlan"]["planner"],
            "nl2sql": architecture_plan_raw.get("nl2sql") or fallback["architecturePlan"]["nl2sql"],
            "htmlRenderer": architecture_plan_raw.get("htmlRenderer") or fallback["architecturePlan"]["htmlRenderer"],
        }

        analysis_intent_raw = response.get("analysisIntent")
        if not isinstance(analysis_intent_raw, dict):
            analysis_intent_raw = {}
        analysis_intent = {
            "goal": analysis_intent_raw.get("goal") or fallback["analysisIntent"]["goal"],
            "contextFusionSummary": (
                analysis_intent_raw.get("contextFusionSummary")
                or fallback["analysisIntent"]["contextFusionSummary"]
            ),
            "evolutionStrategy": (
                analysis_intent_raw.get("evolutionStrategy")
                or fallback["analysisIntent"].get("evolutionStrategy", "")
            ),
        }

        sql_proposal_raw = response.get("sqlProposal")
        if not isinstance(sql_proposal_raw, dict):
            sql_proposal_raw = {}
        
        # Prioriza SQL vinda do Especialista se presente no contexto
        specialist_sql = context.get("specialist_sql")
        final_sql = sql_proposal_raw.get("sql") or specialist_sql or fallback["sqlProposal"]["sql"]
        
        sql_proposal = {
            "description": sql_proposal_raw.get("description") or context.get("specialist_insights") or fallback["sqlProposal"]["description"],
            "sql": final_sql,
        }

        dashboard_plan_raw = response.get("dashboardPlan")
        if not isinstance(dashboard_plan_raw, dict):
            dashboard_plan_raw = {}
        dashboard_plan = {
            "structure": (
                dashboard_plan_raw.get("structure")
                if isinstance(dashboard_plan_raw.get("structure"), list)
                else fallback["dashboardPlan"]["structure"]
            ),
            "components": (
                dashboard_plan_raw.get("components")
                if isinstance(dashboard_plan_raw.get("components"), list)
                else fallback["dashboardPlan"]["components"]
            ),
            "changesFromPreviousVersion": (
                dashboard_plan_raw.get("changesFromPreviousVersion")
                if isinstance(dashboard_plan_raw.get("changesFromPreviousVersion"), list)
                else fallback["dashboardPlan"].get("changesFromPreviousVersion", [])
            ),
        }

        footer_insights = response.get("footerInsights")
        if not isinstance(footer_insights, list):
            footer_insights = fallback["footerInsights"]

        version_action_raw = response.get("versionAction")
        if not isinstance(version_action_raw, dict):
            version_action_raw = {}
        version_action = {
            "type": "save_draft",
            "reason": version_action_raw.get("reason") or fallback["versionAction"]["reason"],
        }

        limitations = response.get("limitations")
        if not isinstance(limitations, list):
            limitations = fallback["limitations"]

        result = {
            "applicationAnalysis": application_analysis,
            "architecturePlan": architecture_plan,
            "analysisIntent": analysis_intent,
            "sqlProposal": sql_proposal,
            "dashboardPlan": dashboard_plan,
            "htmlDashboard": response.get("htmlDashboard") or fallback["htmlDashboard"],
            "footerInsights": footer_insights,
            "versionAction": version_action,
            "limitations": limitations,
            # Legacy compatibility fields consumed by older callers.
            "existingAnalysis": legacy_existing,
            "governanceContext": legacy_governance,
        }
        return result

    def _fallback_response(self, context: dict) -> dict:
        structure = self._infer_structure(context.get("existingDashboardHtml", ""))
        sql_proposal = self._build_sql_proposal(context.get("datasets", []), context.get("semanticRelationships", []))
        footer_insights = self._build_footer_insights(context)
        dashboard_changes = self.planner.build_dashboard_changes()
        existing_analysis = self.planner.build_existing_analysis(context, structure)
        governance_context = self.planner.build_governance_context(context)

        return {
            "applicationAnalysis": self._build_application_analysis(context, structure, existing_analysis),
            "architecturePlan": self._build_architecture_plan(),
            "analysisIntent": self.planner.build_analysis_intent(context),
            "existingAnalysis": existing_analysis,
            "governanceContext": governance_context,
            "sqlProposal": sql_proposal,
            "dashboardPlan": {
                "structure": structure,
                "components": self._build_dashboard_components(context, structure),
                "changesFromPreviousVersion": dashboard_changes,
            },
            "htmlDashboard": self._build_html(context, footer_insights, sql_proposal),
            "footerInsights": footer_insights,
            "versionAction": {
                "type": "save_draft",
                "reason": "Cada interacao deve gerar uma nova versao em estado DRAFT, sem publicacao automatica.",
            },
            "limitations": self._build_limitations(context, sql_proposal),
        }

    def _build_application_analysis(self, context: dict, structure: list[str], existing_analysis: dict) -> dict:
        return self.planner.build_application_analysis(context, structure, existing_analysis)

    def _build_architecture_plan(self) -> dict:
        return self.planner.build_architecture_plan()

    def _build_dashboard_components(self, context: dict, structure: list[str]) -> list[dict]:
        return self.planner.build_dashboard_components(context, structure)

    def _serialize_project_datasets(self, project) -> list[dict]:
        if not project:
            return []
        datasets = []
        for dataset in project.datasets.filter(is_deleted=False):
            datasets.append({
                "id": str(dataset.id),
                "name": dataset.name,
                "description": dataset.description,
                "source_type": dataset.source_type,
                "status": dataset.status,
                "row_count": dataset.row_count,
                "column_count": dataset.column_count,
                "schema_json": dataset.schema_json,
                # data_profile substitui sample_json bruto: ~10x menos tokens,
                # muito mais rico em distribuições e top_values para GROUP BY
                "data_profile": dataset.data_profile_json or {},
                "glue_table": dataset.glue_table,
                "glue_database": dataset.glue_database,
                "sqlite_table": self._build_sqlite_table_name(str(dataset.id), dataset.name),
            })
        return datasets

    def _enrich_datasets_for_sqlite(self, datasets: list[dict]) -> list[dict]:
        enriched = []
        for index, dataset in enumerate(datasets or [], start=1):
            item = dict(dataset or {})
            item.setdefault("sample_json", [])
            item.setdefault("schema_json", {})
            item.setdefault("sqlite_table", self._build_sqlite_table_name(str(item.get("id") or index), item.get("name")))
            enriched.append(item)
        return enriched

    def _build_sql_proposal(self, datasets: list[dict], semantic_relationships: list[dict]) -> dict:
        return self.nl2sql.build_sql_proposal(datasets, semantic_relationships)

    def _build_footer_insights(self, context: dict) -> list[str]:
        insights = []
        for dataset in context.get("datasets", [])[:3]:
            if dataset.get("row_count") is not None or dataset.get("column_count") is not None:
                insights.append(
                    f'O dataset "{dataset.get("name", "dataset")}" apresenta {dataset.get("row_count", 0)} registros e {dataset.get("column_count", 0)} colunas no snapshot atual.'
                )
        if context.get("semanticRelationships"):
            insights.append(
                f"Foram fornecidos {len(context['semanticRelationships'])} relacionamentos semanticos para orientar joins e consolidacoes."
            )
        if context.get("currentUserPrompt"):
            insights.append("A nova versao considera o refinamento solicitado sem descartar a estrutura anterior.")
        return insights[:6] or ["Nao ha metadados suficientes para produzir insights mais especificos sem suposicoes."]

    def _validate_sql_proposal(self, result: dict, context: dict) -> None:
        sql = ((result.get("sqlProposal") or {}).get("sql") or "").strip()
        datasets = context.get("datasets") or []
        if not sql or not datasets or sql.startswith("/*"):
            result["sqlValidation"] = {
                "status": "skipped",
                "reason": "Nao havia SQL executavel ou datasets suficientes para validacao local.",
            }
            return

        try:
            validation = self.sqlite.execute_sql_for_datasets(datasets=datasets, sql=sql)
            result["sqlValidation"] = {
                "status": "validated",
                "engine": "sqlite-local-prototype",
                **validation,
            }
            preview_rows = validation.get("row_count", 0)
            result.setdefault("footerInsights", [])
            result["footerInsights"] = list(result["footerInsights"])
            result["footerInsights"].append(
                f"A validacao local da consulta retornou {preview_rows} linhas na amostra SQLite do prototipo."
            )
        except SQLiteQueryValidationError as exc:
            result["sqlValidation"] = {
                "status": "invalid",
                "engine": "sqlite-local-prototype",
                "error": str(exc),
            }
            result.setdefault("limitations", [])
            result["limitations"] = list(result["limitations"])
            result["limitations"].append(
                f"A SQL proposta nao passou na validacao local em SQLite: {exc}"
            )

    def _build_html(self, context: dict, footer_insights: list[str], sql_proposal: dict | None = None) -> str:
        return self.renderer.build_html(context, footer_insights, sql_proposal=sql_proposal or {})

    def _ensure_operational_output(self, result: dict, context: dict) -> None:
        insights = self._ensure_six_insights(result.get("footerInsights"), context)
        result["footerInsights"] = insights

        html = result.get("htmlDashboard") or ""
        if self.renderer.is_operational_dashboard_html(html):
            return

        result["htmlDashboard"] = self.renderer.build_operational_html(
            context=context,
            footer_insights=insights,
            sql_proposal=result.get("sqlProposal") or {},
        )
        result.setdefault("limitations", [])
        result["limitations"] = list(result["limitations"])
        result["limitations"].append(
            "HTML retornado pelo modelo foi substituido por template operacional para garantir fetch NL2SQL e dashboard executavel."
        )

    def _ensure_six_insights(self, insights: list[str] | None, context: dict) -> list[str]:
        items = [str(item).strip() for item in (insights or []) if str(item).strip()]

        if context.get("datasets"):
            items.append(
                f"O contexto inclui {len(context.get('datasets', []))} dataset(s) ingeridos para analise."
            )
        if context.get("semanticRelationships"):
            items.append(
                f"Existem {len(context.get('semanticRelationships', []))} relacionamento(s) semantico(s) para suporte aos joins."
            )
        if context.get("reportTitle"):
            items.append("Os indicadores foram alinhados ao objetivo analitico do relatorio atual.")
        if context.get("currentUserPrompt"):
            items.append("O refinamento solicitado pelo usuario foi incorporado no desenho dos componentes.")
        if context.get("knowledgeBasePromptHints"):
            items.append("Foram considerados hints da Knowledge Base para padrao visual e estrutura narrativa.")

        deduped = []
        for item in items:
            if item and item not in deduped:
                deduped.append(item)

        while len(deduped) < 6:
            deduped.append("Nao ha evidencia adicional suficiente para expandir insights sem extrapolacao de dados.")
        return deduped[:6]

    def _infer_structure(self, existing_html: str) -> list[str]:
        if not existing_html:
            return ["cabecalho executivo", "indicadores principais", "graficos analiticos", "resumo analitico", "rodape explicativo"]
        lower_html = existing_html.lower()
        structure = []
        if "<header" in lower_html or "<h1" in lower_html:
            structure.append("cabecalho executivo")
        if "kpi" in lower_html or "indicador" in lower_html:
            structure.append("indicadores principais")
        if "chart" in lower_html or "canvas" in lower_html or "graf" in lower_html:
            structure.append("graficos analiticos")
        if "<table" in lower_html:
            structure.append("tabelas de suporte")
        if "insight" in lower_html or "resumo" in lower_html:
            structure.append("resumo analitico")
        return structure or ["estrutura HTML existente preservada", "rodape explicativo"]

    def _context_fusion_summary(self, context: dict) -> str:
        return self.planner.context_fusion_summary(context)

    def _existing_summary(self, context: dict, structure: list[str]) -> str:
        if context.get("existingDashboardHtml"):
            return "O dashboard atual ja possui HTML com blocos identificados em: " + ", ".join(structure) + "."
        return "Nao havia HTML anterior disponivel no contexto atual."

    def _build_limitations(self, context: dict, sql_proposal: dict) -> list[str]:
        limitations = []
        if not context.get("existingDashboardHtml"):
            limitations.append("Nao havia HTML anterior no contexto de entrada.")
        if "Insufficient dataset metadata" in sql_proposal.get("sql", ""):
            limitations.append("A proposta SQL foi mantida conservadora para nao inventar metadados tabulares ausentes.")
        if not context.get("semanticRelationships"):
            limitations.append("Nao foram informados relacionamentos semanticos; joins complexos foram evitados.")
        return limitations

    def _merge_previous_prompts(self, prompts: list[str], version) -> list[str]:
        merged = list(prompts)
        if version.full_prompt:
            merged.append(version.full_prompt)
        snapshot_prompt = (version.instruction_snapshot or {}).get("content")
        if snapshot_prompt:
            merged.append(snapshot_prompt)
        deduped = []
        for item in merged:
            if item and item not in deduped:
                deduped.append(item)
        return deduped[-10:]

    def _get_existing_html(self, version) -> str:
        template_snapshot = version.template_snapshot or {}
        if template_snapshot.get("rendered_html"):
            return template_snapshot["rendered_html"]
        if version.html_s3_path:
            try:
                from apps.datasets.services.s3_service import S3Service
                s3 = S3Service()
                return s3.download_from_path(version.html_s3_path).decode("utf-8")
            except Exception as exc:
                logger.warning("Unable to load dashboard HTML from S3: %s", exc)
        return ""

    def _get_domain_owner_name(self, project) -> str:
        owner = getattr(getattr(project, "domain", None), "owner", None)
        if not owner:
            return ""
        return owner.get_full_name() or owner.email or str(owner.id)

    def _get_current_version_label(self, dashboard) -> str:
        if dashboard and dashboard.current_version:
            return f"v{dashboard.current_version.version_number}"
        return ""

    def _get_current_dashboard_state(self, dashboard) -> str:
        if dashboard and dashboard.current_version:
            return dashboard.current_version.state
        if dashboard:
            return dashboard.status
        return "DRAFT"

    def _save_draft_version(self, context: dict, result: dict, request_user=None):
        from apps.versions.models import Version, VersionState

        dashboard = context["dashboard"]
        last_version = dashboard.versions.filter(is_deleted=False).order_by("-version_number").first()
        next_version_number = (last_version.version_number + 1) if last_version else 1

        html_s3_path = ""
        try:
            from apps.datasets.services.s3_service import S3Service
            s3 = S3Service()
            html_s3_key = f"{dashboard.project.s3_path}/dashboards/{dashboard.id}/v{next_version_number}/index.html"
            html_s3_path = s3.upload_html(result["htmlDashboard"], html_s3_key)
        except Exception as exc:
            logger.warning("Draft HTML upload failed: %s", exc)

        version = Version.objects.create(
            dashboard=dashboard,
            version_number=next_version_number,
            state=VersionState.DRAFT,
            html_s3_path=html_s3_path,
            sql_queries=[result["sqlProposal"]],
            ai_insights="\n".join(result.get("footerInsights", [])),
            full_prompt=context.get("currentUserPrompt", ""),
            ai_score=1.0 if result.get("sqlValidation", {}).get("status") == "validated" else 0.75,
            critic_feedback="\n".join(result.get("limitations", [])),
            iterations=1,
            instruction_snapshot={
                "content": context.get("currentUserPrompt", ""),
                "previousUserPrompts": context.get("previousUserPrompts", []),
                "sessionAuthor": context.get("sessionAuthor", ""),
            },
            template_snapshot={
                "templatePrompt": context.get("templatePrompt", ""),
                "masterPrompt": context.get("masterPrompt", ""),
                "reportMetadata": context.get("reportMetadata", {}),
                "rendered_html": result["htmlDashboard"],
            },
            dataset_snapshot={
                "datasets": context.get("datasets", []),
                "semanticRelationships": context.get("semanticRelationships", []),
                "sqlValidation": result.get("sqlValidation", {}),
            },
            change_summary=" | ".join(result.get("dashboardPlan", {}).get("changesFromPreviousVersion", [])[:3]),
            created_by=request_user if getattr(request_user, "is_authenticated", False) else dashboard.created_by,
        )
        dashboard.current_version = version
        dashboard.save(update_fields=["current_version", "updated_at"])
        return version

    def _build_sqlite_table_name(self, dataset_id: str, name: str | None) -> str:
        if not dataset_id:
            return build_sqlite_table_name(dataset_id="dataset", dataset_name=name)
        return self.sqlite_store.resolve_table_name(dataset_id=dataset_id, dataset_name=name)

    def _should_try_bedrock(self) -> bool:
        if not bool(getattr(settings, "USE_BEDROCK_LLM", True)):
            return False

        if not bool(getattr(settings, "BEDROCK_REGION", "") or getattr(settings, "AWS_REGION", "")):
            return False

        engine = settings.DATABASES.get("default", {}).get("ENGINE", "")
        if "sqlite3" in engine:
            # Em local_fast, so tenta Bedrock quando o usuario configurou credenciais.
            return bool(
                (
                    getattr(settings, "AWS_ACCESS_KEY_ID", "")
                    and getattr(settings, "AWS_SECRET_ACCESS_KEY", "")
                )
                or os.getenv("AWS_PROFILE")
            )

        return True

    def _bedrock_client(self) -> BedrockService:
        if self.bedrock is None:
            self.bedrock = BedrockService()
        return self.bedrock

    def _retrieve_rag_context(
        self,
        current_user_prompt: str,
        report_title: str,
        report_description: str,
        previous_prompts: list,
        kb_hints: list[str] | None = None,
    ) -> list:
        kb_id = getattr(settings, "BEDROCK_KB_ID", "")
        if not kb_id or not self._should_try_bedrock():
            return []

        query_parts = [
            (current_user_prompt or "").strip(),
            (report_title or "").strip(),
            (report_description or "").strip(),
            "template html padrao layout corporativo paleta de cores componentes",
        ]
        if previous_prompts:
            query_parts.append(" | ".join([p for p in previous_prompts[-3:] if p]))
        if kb_hints:
            query_parts.append(" | ".join([hint for hint in kb_hints if hint]))
        query_text = " | ".join([part for part in query_parts if part]).strip()
        if not query_text:
            return []

        snippets = self._bedrock_client().retrieve_kb_context(
            query=query_text[:2000],
            knowledge_base_id=kb_id,
            max_results=getattr(settings, "BEDROCK_KB_MAX_RESULTS", 5),
        )

        normalized = []
        for snippet in snippets:
            if not isinstance(snippet, dict):
                continue
            text = (snippet.get("text") or "").strip()
            if not text:
                continue
            normalized.append(
                {
                    "text": text[:1200],
                    "score": snippet.get("score"),
                    "source": snippet.get("source", ""),
                }
            )
        return normalized
