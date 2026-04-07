import json
import logging
from typing import Dict, Any, List

from django.conf import settings
from apps.ai_engine.services.bedrock_service import BedrockService

logger = logging.getLogger(__name__)

SUPERVISOR_SYSTEM_PROMPT = """Você é o Supervisor Analítico da NTT DATA - Agent-BI.
Sua única responsabilidade é classificar a intenção (intent) da requisição do usuário em uma das três rotas possíveis:

1. "ROUTE_NL2SQL": Quando o usuário solicita tabelas, listagens simples, filtros diretos de banco de dados, ou agregações padrões que podem ser resolvidas com SQL básico (COUNT, SUM, GROUP BY).
2. "ROUTE_PANDAS": Quando o usuário pede análises estatísticas complexas, correlações (Scatter), projeções e previsões de valor futuro (Forecast), identificação de anomalias, ou perguntas que exijam cálculos matemáticos avançados via Python.
3. "ROUTE_KB_RAG": Quando a pergunta for conceitual, regulamentar ou perguntar sobre os dados num sentido de regras de negócio ou definições, sem precisar de cálculos.

## Saída Exigida
Você DEVE retornar APENAS um JSON válido contendo os seguintes campos, e NADA MAIS (nenhum texto introdutório ou markdown extra):
{
  "reasoning": "Sua justificativa curta do porquê escolheu a rota",
  "route": "ROUTE_NL2SQL" | "ROUTE_PANDAS" | "ROUTE_KB_RAG"
}
"""

class SupervisorAgent:
    """
    Agente responsável por rotear a intenção do usuário para o Sub-Agente especialista 
    correto (NL2SQL para dados tabelares, Pandas para estatística, KB para RAG).
    """
    def __init__(self):
        self.bedrock_service = BedrockService()

    def determine_route(self, user_prompt: str, datasets_metadata: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Invoca a LLM subjacente para decidir o melhor especialista.
        """
        logger.info("[Supervisor] Iniciando análise de intenção.")
        
        # Constrói o contexto resumido
        context_str = "\nDatasets Disponíveis para contexto:\n"
        if datasets_metadata:
            for ds in datasets_metadata:
                context_str += f"- {ds.get('name', 'N/A')}: {ds.get('description', '')}\n"
        
        prompt = f"Pergunta do Usuário: '{user_prompt}'\n{context_str}\nQual a melhor rota de processamento?"
        
        try:
            response_text = self.bedrock_service.generate_text(
                prompt=prompt,
                system_prompt=SUPERVISOR_SYSTEM_PROMPT,
                max_tokens=300
            )
            
            # Sanitiza a resposta caso a llm ponha ```json ... ```
            cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
            decision_json = json.loads(cleaned_text)
            
            route = decision_json.get("route", "ROUTE_NL2SQL")
            logger.info(f"[Supervisor] Rota Selecionada: {route} - Motivo: {decision_json.get('reasoning')}")
            
            return decision_json
            
        except json.JSONDecodeError as e:
            logger.error(f"[Supervisor] Falha ao parear JSON da LLM: {e}. Fallback para ROUTE_NL2SQL.")
            return {
                "reasoning": "Fallback automático devido à falha de parse.",
                "route": "ROUTE_NL2SQL"
            }
        except Exception as e:
            logger.error(f"[Supervisor] Falha na análise: {e}. Fallback para ROUTE_NL2SQL.")
            return {
                "reasoning": "Erro na invocação da LLM.",
                "route": "ROUTE_NL2SQL"
            }
