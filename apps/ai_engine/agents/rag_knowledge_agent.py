import logging
from typing import Dict, Any

from django.conf import settings
from apps.ai_engine.services.bedrock_service import BedrockService

logger = logging.getLogger(__name__)

RAG_AGENT_SYSTEM_PROMPT = """Você é o Consultor de Diretrizes e Engenheiro de Conhecimento da NTT DATA - Agent-BI.
Sua missão é interpretar a Base de Conhecimento para fornecer fórmulas e regras técnicas infalíveis ao orquestrador.

Você deve extrair com PRIORIDADE MÁXIMA:
1. **Fórmulas Matemáticas e Métricas**: Como calcular exatamente os indicadores mencionados (ex: "Score = (A*0.4) + B"). Extraia variáveis e pesos.
2. **Regras de Negócio**: Condicionais e gatilhos (ex: "Se inadimplência > 5%, sinalizar como ALTO RISCO").
3. **Identidade Visual**: Logos (URLs), cores e padrões de design obrigatórios.

## Saída Exigida (JSON):
Retorne um JSON válido com:
{
  "guidelines": "Resumo executivo das regras para o dashboard",
  "visual_assets": ["lista", "de", "urls", "ou", "logos"],
  "business_rules": "DESCRIÇÃO DETALHADA DAS FÓRMULAS E REGRAS DE CÁLCULO ENCONTRADAS",
  "answer": "Resposta direta e técnica para a pergunta do usuário"
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
