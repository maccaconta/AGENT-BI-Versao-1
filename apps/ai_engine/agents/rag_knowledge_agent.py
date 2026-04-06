import logging
from typing import Dict, Any

from django.conf import settings
from apps.ai_engine.services.bedrock_service import BedrockService

logger = logging.getLogger(__name__)

RAG_AGENT_SYSTEM_PROMPT = """Você é o Especialista Semântico de Base de Conhecimento Corporativa da NTT DATA - Agent-BI.
Sua única responsabilidade é localizar respostas precisas em manuais, regras de negócios e diretrizes (extraídos da Base de Conhecimento) para perguntas operacionais e conceituais do usuário.
Você deve responder diretamente a pergunta de forma didática, concisa e aderente à marca NTT DATA.

Se a Base de Conhecimento (Contexto) não fornecer as respostas, NÃO invente dados. Diga que as diretrizes não especificam essa regra.
"""

class RAGKnowledgeAgent:
    """
    Sub-Agente especializado em isolar a chamda RAG do Bedrock para perguntas de diretrizes institucionais.
    """
    def __init__(self):
        self.bedrock_service = BedrockService()

    def query_knowledge(self, user_prompt: str, rag_context: str = "") -> Dict[str, Any]:
        """
        Responde a uma pergunta baseada estritamente no rag_context obtido previamente (ex: Retrieve do Bedrock).
        """
        logger.info("[RAG_Agent] Buscando respostas no contexto da base de conhecimento.")
        
        prompt = f"""
Pergunta Corporativa: "{user_prompt}"

=== Contexto Recuperado (RAG) ===
{rag_context if rag_context else "Nenhum contexto recuperado da base de conhecimento."}
=================================

Por favor, responda baseando-se única e exclusivamente no contexto provido acima.
        """
        
        try:
            response_text = self.bedrock_service.generate_text(
                prompt=prompt,
                system_prompt=RAG_AGENT_SYSTEM_PROMPT,
                max_tokens=1500
            )
            
            return {
                "specialist": "KB_RAG",
                "answer": response_text
            }
            
        except Exception as e:
            logger.error(f"[RAG_Agent] Falha na consulta RAG: {e}")
            return {
                "specialist": "KB_RAG",
                "error": str(e),
                "answer": "Não foi possível recuperar a informação nas diretrizes corporativas devido a um erro de serviço."
            }
