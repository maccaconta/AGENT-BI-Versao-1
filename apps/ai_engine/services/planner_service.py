"""
apps.ai_engine.services.planner_service
Camada Planner para orquestracao analitica incremental.
"""
from __future__ import annotations


class DashboardPlannerService:
    CONTEXT_FUSION_KEYS = [
        "templatePrompt",
        "masterPrompt",
        "reportDescription",
        "reportMetadata",
        "datasets",
        "semanticRelationships",
        "previousUserPrompts",
        "currentUserPrompt",
        "existingDashboardHtml",
    ]

    def build_analysis_intent(self, context: dict) -> dict:
        return {
            "goal": context.get("currentUserPrompt") or context.get("reportDescription") or "Evoluir o dashboard existente.",
            "contextFusionSummary": self.context_fusion_summary(context),
            "evolutionStrategy": "Preservar o HTML e a estrutura atual, adicionando apenas refinamentos incrementais e auditaveis.",
        }

    def build_existing_analysis(self, context: dict, structure: list[str]) -> dict:
        return {
            "whatAlreadyExists": self._existing_summary(context, structure),
            "whatWillBeKept": "Cabecalho, blocos validos e consistencia visual ja existente.",
            "whatWillBeChanged": "Narrativa analitica, SQL de suporte e elementos afetados pelo prompt atual.",
            "whatWillBeAdded": "Resumo analitico verificavel e reforco de contexto de governanca.",
        }

    def build_governance_context(self, context: dict) -> dict:
        return {
            "dataDomain": context.get("dataDomain", ""),
            "dataOwner": context.get("domainDataOwner", ""),
            "confidentiality": context.get("dataConfidentiality", ""),
        }

    def build_application_analysis(self, context: dict, structure: list[str], existing_analysis: dict) -> dict:
        dataset_count = len(context.get("datasets") or [])
        relationship_count = len(context.get("semanticRelationships") or [])
        has_existing_html = bool(context.get("existingDashboardHtml"))

        existing_modules = (
            "Backend incremental ativo no endpoint /api/v1/copilot/generate com versoes DRAFT e validacao SQL em SQLite; "
            f"frontend envia contexto acumulado e HTML existente; blocos identificados: {', '.join(structure)}."
        )
        capabilities = (
            f"Fusao de contexto (template/master/historico/prompt), {dataset_count} datasets no payload atual, "
            f"{relationship_count} relacionamentos semanticos e renderizacao HTML incremental."
        )

        gaps = []
        if not has_existing_html:
            gaps.append("Sem HTML previo no contexto desta iteracao.")
        if not relationship_count:
            gaps.append("Sem relacionamentos semanticos para joins complexos.")
        if dataset_count == 0:
            gaps.append("Sem datasets suficientes para analise tabular auditavel.")
        if not gaps:
            gaps.append(existing_analysis.get("whatWillBeChanged", "Aprimorar o plano analitico incremental sem romper o que ja funciona."))

        return {
            "existingModules": existing_modules,
            "capabilitiesIdentified": capabilities,
            "gaps": " ".join(gaps),
        }

    def build_architecture_plan(self) -> dict:
        return {
            "planner": (
                "Fundir templatePrompt, masterPrompt, previousUserPrompts, currentUserPrompt e reportMetadata "
                "para definir objetivo, metricas e escopo incremental."
            ),
            "nl2sql": (
                "Gerar SQL auditavel apenas com datasets e semanticRelationships fornecidos, "
                "validar em SQLite local e registrar limitacoes quando houver falha."
            ),
            "htmlRenderer": (
                "Renderizar HTML final com base no plano e nos dados preparados, preservando estrutura existente "
                "e sem acesso direto ao banco."
            ),
        }

    def build_dashboard_components(self, context: dict, structure: list[str]) -> list[dict]:
        components = []
        if any("cabecalho" in item for item in structure):
            components.append({
                "type": "header",
                "title": context.get("reportTitle") or context.get("dashboardName") or "Dashboard Corporativo",
            })
        if any("indicadores" in item for item in structure):
            components.append({
                "type": "big_numbers",
                "dataSource": "sqlProposal",
            })
        if any("graficos" in item for item in structure):
            components.append({
                "type": "charts",
                "dataSource": "sqlProposal",
            })
        if any("tabelas" in item for item in structure):
            components.append({
                "type": "tables",
                "dataSource": "sqlProposal",
            })
        components.append({
            "type": "insights_footer",
            "dataSource": "footerInsights",
        })
        return components

    def build_dashboard_changes(self) -> list[str]:
        return [
            "Preservar a base do dashboard existente.",
            "Aplicar refinamento incremental orientado pelo prompt atual.",
            "Registrar a nova iteracao como DRAFT.",
        ]

    def context_fusion_summary(self, context: dict) -> str:
        used = []
        for key in self.CONTEXT_FUSION_KEYS:
            if context.get(key):
                used.append(key)
        return "Contexto fundido a partir de: " + ", ".join(used) if used else "Contexto minimo disponivel."

    def _existing_summary(self, context: dict, structure: list[str]) -> str:
        if context.get("existingDashboardHtml"):
            return "O dashboard atual ja possui HTML com blocos identificados em: " + ", ".join(structure) + "."
        return "Nao havia HTML anterior disponivel no contexto atual."

