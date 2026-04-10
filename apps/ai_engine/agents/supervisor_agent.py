import json
import logging
from typing import Dict, Any, List

from django.conf import settings
from apps.ai_engine.services.bedrock_service import BedrockService
from apps.ai_engine.services.prompt_service import PromptService

logger = logging.getLogger(__name__)

SUPERVISOR_SYSTEM_PROMPT = """Você é o Supervisor Analítico de Alta Performance da NTT DATA. 
Sua missão é garantir que a pergunta do usuário seja respondida pelo especialista com maior capacidade analítica.

## REGRAS DE ROTEAMENTO (MANDATÓRIAS):

1. **ROUTE_PANDAS**: Rota padrão e OBRIGATÓRIA para qualquer tema que envolva:
   - **Risco de Crédito**, Score, Rating, Probabilidade de Default (PD).
   - **Inadimplência**, Análise de Carteira, Exposição, Projeções Financeiras.
   - Análises que exijam criação de novas colunas ou cálculos avançados.
   - **Sempre que o contexto mencionar diretrizes de um ESPECIALISTA DE DOMÍNIO.**

2. **ROUTE_NL2SQL**: Use EXCLUSIVAMENTE para buscas de dados "crus":
   - Listagens simples de clientes ou transações.
   - Filtros básicos de uma única tabela sem necessidade de inteligência estatística.
   - Perguntas do tipo "Quais são os clientes de SP?" ou "Quantos registros temos?".

3. **ROUTE_KB_RAG**: Use apenas para definições conceituais ou normas de compliance.

## Saída Exigida
Retorne estritamente um JSON:
{
  "reasoning": "Justificativa da escolha da rota analítica",
  "route": "ROUTE_PANDAS" | "ROUTE_NL2SQL" | "ROUTE_KB_RAG"
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
        Determina a melhor rota para a solicitação do usuário.
        """
        # Carrega o system prompt dinâmico se disponível no BD
        system_prompt = PromptService.get_system_prompt("SupervisorAgent", SUPERVISOR_SYSTEM_PROMPT)
        
        prompt = f"""
Pergunta do Usuário: "{user_prompt}"

=== METADADOS DOS DATASETS DISPONÍVEIS ===
{json.dumps(datasets_metadata, indent=2, ensure_ascii=False) if datasets_metadata else "Nenhum dataset carregado."}

Analise a pergunta e o contexto para decidir a melhor rota.
"""
        
        try:
            result = self.bedrock_service.invoke_with_json_output(
                system_prompt=system_prompt,
                user_message=prompt,
                temperature=0.1
            )
            
            # Usa o parser resiliente do serviço para evitar falhas de formatação
            decision_json = self.bedrock_service._parse_json_response(response_text)
            
            if not decision_json:
                raise ValueError("Supervisor não conseguiu gerar uma decisão JSON válida.")
            
            route = decision_json.get("route", "ROUTE_NL2SQL")
            
            # Validação de rota: garante que seja uma das opções válidas
            valid_routes = ["ROUTE_PANDAS", "ROUTE_NL2SQL", "ROUTE_KB_RAG"]
            if route not in valid_routes:
                logger.warning(f"[Supervisor] Rota inválida '{route}' retornada pela LLM. Usando ROUTE_PANDAS como padrão.")
                route = "ROUTE_PANDAS"
                decision_json["route"] = route
                decision_json["reasoning"] += " (rota corrigida para análise estatística por segurança)"
            
            logger.info(f"[Supervisor] Rota Selecionada: {route} - Motivo: {decision_json.get('reasoning')}")
            
            return decision_json
            
        except json.JSONDecodeError as e:
            logger.error(f"[Supervisor] Falha ao parsear JSON da LLM: {e}. Fallback para ROUTE_PANDAS (risco-sensível).")
            return {
                "reasoning": "Fallback automático devido à falha de parse JSON. Usando análise estatística por segurança.",
                "route": "ROUTE_PANDAS"
            }
        except Exception as e:
            logger.error(f"[Supervisor] Falha na análise: {e}. Fallback para ROUTE_PANDAS (risco-sensível).")
            return {
                "reasoning": "Erro na invocação da LLM. Usando análise estatística por segurança.",
                "route": "ROUTE_PANDAS"
            }
