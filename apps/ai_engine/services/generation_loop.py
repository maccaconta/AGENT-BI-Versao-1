"""
apps.ai_engine.services.generation_loop
Camada de compatibilidade do pipeline legado.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from apps.ai_engine.services.incremental_dashboard_agent import IncrementalDashboardAgentService


@dataclass
class GenerationLoopResult:
    final_html: str = ""
    final_sql_queries: list = field(default_factory=list)
    final_insights: str = ""
    final_score: float = 0.0
    critique: Optional[object] = None
    total_iterations: int = 0
    total_time_seconds: float = 0.0
    iteration_history: list = field(default_factory=list)
    succeeded: bool = False
    error_message: str = ""
    raw_result: dict = field(default_factory=dict)


class AIGenerationLoop:
    """
    Wrapper para manter compatibilidade com chamadas antigas.
    Internamente delega para o agente incremental unificado.
    """

    def __init__(self):
        self.service = IncrementalDashboardAgentService()

    def run(
        self,
        instruction: str,
        dataset,
        template_hints: str = "",
        job_callback=None,
    ) -> GenerationLoopResult:
        loop_start = time.time()
        result = GenerationLoopResult()

        if job_callback:
            job_callback(iteration=1, score=0.0, status="iterating")

        try:
            payload = {
                "project_id": str(dataset.project_id),
                "dashboardName": getattr(dataset.project, "name", "Dashboard"),
                "reportTitle": getattr(dataset.project, "name", "Dashboard"),
                "reportDescription": getattr(dataset.project, "description", ""),
                "templatePrompt": template_hints,
                "currentUserPrompt": instruction,
                "datasets": self.service._serialize_project_datasets(dataset.project),
            }
            generated = self.service.generate(payload, request_user=None, save_version=False)

            validation = generated.get("sqlValidation", {})
            score = 1.0 if validation.get("status") == "validated" else 0.75

            result.final_html = generated.get("htmlDashboard", "")
            sql = (generated.get("sqlProposal") or {}).get("sql")
            result.final_sql_queries = [generated.get("sqlProposal")] if sql else []
            result.final_insights = "\n".join(generated.get("footerInsights", []))
            result.final_score = score
            result.total_iterations = 1
            result.total_time_seconds = time.time() - loop_start
            result.iteration_history = [{
                "iteration": 1,
                "score": score,
                "grade": "A" if score >= 0.9 else "B",
                "feedback": "Pipeline legado redirecionado para o agente incremental unificado.",
                "issues_count": 0 if validation.get("status") == "validated" else 1,
                "exec_time_seconds": result.total_time_seconds,
            }]
            result.succeeded = True
            result.raw_result = generated

            if job_callback:
                job_callback(iteration=1, score=score, status="completed")
            return result
        except Exception as exc:
            result.error_message = str(exc)
            result.total_time_seconds = time.time() - loop_start
            if job_callback:
                job_callback(iteration=1, score=0.0, status="failed")
            return result
