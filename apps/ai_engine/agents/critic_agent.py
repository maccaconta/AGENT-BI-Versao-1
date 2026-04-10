"""
apps.ai_engine.agents.critic_agent
────────────────────────────────────
Critic Agent: avalia qualidade dos dashboards gerados com score 0.0-1.0.
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from apps.ai_engine.services.bedrock_service import BedrockService, BedrockInvocationError
from apps.ai_engine.services.prompt_service import PromptService
from apps.ai_engine.prompts.critic_prompt import (
    CRITIC_SYSTEM_PROMPT,
    build_critic_prompt,
)

logger = logging.getLogger(__name__)


@dataclass
class CriticResult:
    """Resultado estruturado do Critic Agent."""
    score: float = 0.0
    governance_score: float = 0.0
    coverage_score: float = 0.0
    sql_score: float = 0.0
    python_score: float = 0.0
    visual_score: float = 0.0
    feedback: str = ""
    issues: list = field(default_factory=list)
    suggestions: list = field(default_factory=list)
    approved: bool = False
    execution_time_seconds: float = 0.0
    raw_response: dict = field(default_factory=dict)

    @property
    def passes_threshold(self) -> bool:
        from django.conf import settings
        # Rigor aumentado para governança
        threshold = getattr(settings, "AI_MIN_SCORE_THRESHOLD", 0.85)
        return self.score >= threshold and self.governance_score >= 0.8

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "governance_score": self.governance_score,
            "coverage_score": self.coverage_score,
            "sql_score": self.sql_score,
            "python_score": self.python_score,
            "visual_score": self.visual_score,
            "feedback": self.feedback,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "approved": self.approved,
        }


class CriticAgentError(Exception):
    """Erro no Critic Agent."""
    pass


class CriticAgent:
    """
    Critic Agent: avalia rigorosamente os dashboards gerados.
    """

    def __init__(self):
        self.bedrock = BedrockService()

    def evaluate(
        self,
        original_instruction: str,
        generated_html: str,
        sql_queries: list,
        query_results: list,
        schema: dict,
        dataset=None,
        iteration: int = 1,
        python_code: str = "",
        pandas_thought: str = "",
    ) -> CriticResult:
        """
        Avalia um dashboard gerado (SQL + Python + Visual).
        """
        start_time = time.time()
        logger.info(f"Critic Agent: avaliando dashboard. Iteração {iteration}")

        # Construir prompt técnico de avaliação
        prompt = build_critic_prompt(
            original_instruction=original_instruction,
            generated_html=generated_html,
            sql_queries=sql_queries,
            query_results=query_results,
            iteration=iteration,
            schema=schema,
            python_code=python_code,
            pandas_thought=pandas_thought,
        )

        # Buscar Governança Dinâmica (Novo AgentSystemPrompt)
        system_instructions = PromptService.get_system_prompt("CriticAgent", CRITIC_SYSTEM_PROMPT)
        
        if dataset and hasattr(dataset, 'project'):
            from apps.governance.models import GlobalSystemPrompt
            tenant = dataset.project.tenant
            global_policy = GlobalSystemPrompt.objects.filter(tenant=tenant, is_active=True).first()
            if global_policy:
                system_instructions = global_policy.generate_full_system_prompt() + "\n\n" + system_instructions

        # Verificar se o Bedrock está disponível e configurado
        if not self._is_bedrock_available():
            logger.info("Critic Agent: Bedrock indisponível. Pulando avaliação detalhada.")
            return CriticResult(
                score=1.0, 
                governance_score=1.0,
                feedback="Avaliação automática ignorada (Bedrock desativado).",
                approved=True
            )

        # Invocar Bedrock
        try:
            response_data = self.bedrock.invoke_with_json_output(
                system_prompt=system_instructions,
                user_message=prompt,
                temperature=0.1,
            )
        except BedrockInvocationError as e:
            logger.error(f"Critic Agent: erro Bedrock: {e}")
            return CriticResult(
                score=0.3,
                feedback=f"Erro na avaliação automática: {e}. Revisão manual necessária.",
                issues=["Critic Agent indisponível"],
            )

        # Parsear resultado
        result = self._parse_response(response_data)
        result.execution_time_seconds = time.time() - start_time

        logger.info(
            f"Critic Agent: score={result.score:.2f}, gov_score={result.governance_score:.2f}, "
            f"aprovado={result.passes_threshold}, "
            f"tempo={result.execution_time_seconds:.2f}s"
        )

        return result

    def _parse_response(self, data: dict) -> CriticResult:
        """Parseia resposta do Critic em CriticResult."""
        try:
            score = float(data.get("score", 0.0))
            score = max(0.0, min(1.0, score))

            return CriticResult(
                score=score,
                governance_score=float(data.get("governance_score", 0.0)),
                coverage_score=float(data.get("coverage_score", 0.0)),
                sql_score=float(data.get("sql_score", 0.0)),
                python_score=float(data.get("python_score", 0.0)),
                visual_score=float(data.get("visual_score", 0.0)),
                feedback=data.get("feedback", ""),
                issues=data.get("issues", []),
                suggestions=data.get("suggestions", []),
                approved=data.get("approved", score >= 0.85),
                raw_response=data,
            )
        except (ValueError, TypeError) as e:
            logger.error(f"Erro ao parsear resposta do Critic: {e}")
            return CriticResult(
                score=0.5,
                feedback="Erro ao parsear avaliação do Critic.",
                raw_response=data,
            )

    def _is_bedrock_available(self) -> bool:
        """Verifica se o Bedrock está ativo e com chaves configuradas."""
        from django.conf import settings
        
        # 1. Verifica flag global
        use_bedrock = getattr(settings, "USE_BEDROCK_LLM", False)
        if not use_bedrock:
            return False
            
        # 2. Verifica se estamos em teste e se o Bedrock deve ser mockado
        # Em teste, se USE_BEDROCK_LLM é False (já checado acima), retornamos False.
        
        # 3. Verifica chaves mínimas (apenas se não estiver em modo local_fast sem chaves)
        aws_key = getattr(settings, "AWS_ACCESS_KEY_ID", "")
        aws_secret = getattr(settings, "AWS_SECRET_ACCESS_KEY", "")
        
        return bool(aws_key and aws_secret)

    @staticmethod
    def _score_to_grade(score: float) -> str:
        """Converte score numérico em grade letra."""
        if score >= 0.95:
            return "A+"
        elif score >= 0.90:
            return "A"
        elif score >= 0.85:
            return "A-"
        elif score >= 0.80:
            return "B+"
        elif score >= 0.75:
            return "B"
        elif score >= 0.70:
            return "B-"
        elif score >= 0.65:
            return "C+"
        elif score >= 0.60:
            return "C"
        elif score >= 0.50:
            return "D"
        else:
            return "F"
