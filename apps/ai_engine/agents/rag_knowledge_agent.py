import logging
from typing import Dict, Any

from django.conf import settings
from apps.ai_engine.services.bedrock_service import BedrockService

logger = logging.getLogger(__name__)

RAG_AGENT_SYSTEM_PROMPT = """Você é o Consultor de Diretrizes e Regras de Negócio da NTT DATA - Agent-BI.
Sua missão é interpretar o contexto da Base de Conhecimento para fornecer orientações precisas ao orquestrador de dashboards.

Você deve extrair:
1. **Regras de Negócio**: Como calcular métricas específicas mencionadas no contexto.
2. **Identidade Visual**: Logos, cores e padrões de design obrigatórios.
3. **Tom de Voz**: Como os insights devem ser redigidos (ex: executivo, técnico, cauteloso).

## Saída Exigida (JSON):
Retorne um JSON válido com:
{
  "guidelines": "Resumo das regras e padrões identificados para o dashboard",
  "visual_assets": ["lista", "de", "urls", "ou", "logos"],
  "business_rules": "Explicação de fórmulas ou lógicas de negócio encontradas",
  "answer": "Resposta direta para a pergunta do usuário se aplicável"
}
"""

class RAGKnowledgeAgent:
    """
    Assistente ativo que interpreta a base de conhecimento para extrair regras e padrões.
    Pode atuar como ponte para o AWS Bedrock Agent oficial.
    """
    def __init__(self):
        self.bedrock_service = BedrockService()

    def query_knowledge(self, user_prompt: str, rag_context: str = "", trace=None) -> Dict[str, Any]:
        """
        Interpreta o contexto RAG e retorna diretrizes estruturadas.
        """
        logger.info("[Assistente_RAG] Interpretando diretrizes da base de conhecimento.")
        
        if trace:
            trace.log_thought("Assistente RAG", "Consultando a Base de Conhecimento (AWS Bedrock Agent) para alinhar o dashboard às regras de negócio e identidade visual.")

        prompt = f"""
Pergunta do Usuário: "{user_prompt}"

=== Contexto Recuperado da Base de Conhecimento ===
{rag_context if rag_context else "Nenhum contexto recuperado."}
=================================================

Extraia as diretrizes e regras conforme as instruções do sistema.
        """
        
        try:
            if trace:
                trace.start_step("AWS Bedrock Agent: Recuperação")

            result = self.bedrock_service.invoke_with_json_output(
                system_prompt=RAG_AGENT_SYSTEM_PROMPT,
                user_message=prompt,
                temperature=0.1
            )
            
            if trace:
                trace.end_step("AWS Bedrock Agent: Recuperação", message="Conhecimento corporativo recuperado com sucesso.", metadata=result)

            return {
                "specialist": "ASSISTENTE_RAG",
                **result
            }
            
        except Exception as e:
            logger.error(f"[Assistente_RAG] Falha na interpretação RAG: {e}")
            if trace:
                trace.quick_log(trace.trace_id, trace.job_type, "Assistente RAG: Erro", str(e), status="ERROR")
            return {
                "specialist": "ASSISTENTE_RAG",
                "error": str(e),
                "answer": "Falha ao processar diretrizes corporativas.",
                "guidelines": ""
            }
