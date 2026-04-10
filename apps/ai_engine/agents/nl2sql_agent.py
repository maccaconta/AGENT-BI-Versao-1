"""
apps.ai_engine.agents.nl2sql_agent
Agente especialista em geração de SQL complexo (Joins, CTEs, Window Functions) via LLM.
"""
import json
import logging
from typing import Dict, Any, List

from apps.ai_engine.services.bedrock_service import BedrockService
from apps.ai_engine.services.prompt_service import PromptService

logger = logging.getLogger(__name__)

NL2SQL_AGENT_SYSTEM_PROMPT = """Você é o Analista Financeiro Sênior e Especialista em SQL (NL2SQL) da NTT DATA - Agent-BI.
Sua missão é converter perguntas de usuários em consultas SQL estratégicas que forneçam uma visão analítica completa do negócio.

## REGRAS DE INTEGRIDADE ANALÍTICA:
1. **AGREGAÇÃO CONSCIENTE**: Respeite as `usage_instructions` e as flags `can_group`. Se uma coluna tiver `can_group = false`, não a utilize no GROUP BY a menos que seja estritamente necessário para um filtro.
2. **GRANULARIDADE**: Ao gerar JOINs, garanta que a granularidade das tabelas (`granularity`) seja compatível.
3. **Fórmulas de Risco**: Priorize as **REGRAS DE NEGÓCIO ESPECIALIZADAS** fornecidas no contexto. Elas têm prioridade total.

## Saída Exigida (JSON):
{
  "sql": "A consulta SQL gerada",
  "description": "Explicação concisa voltada para o negócio",
  "complexity": "LOW" | "MEDIUM" | "HIGH"
}
"""

class NL2SQLAgent:
    """
    Assistente especializado em traduzir linguagem natural para SQL complexo.
    """
    def __init__(self):
        self.bedrock_service = BedrockService()

    def generate_sql(self, user_prompt: str, datasets: List[Dict[str, Any]], relationships: List[Dict[str, Any]] = None, specialist_context: str = "", trace=None) -> Dict[str, Any]:
        """
        Gera a proposta SQL baseada no contexto tabular e nas métricas da Base de Conhecimento.
        """
        logger.info("[Assistente_NL2SQL] Iniciando geração de SQL com contexto especializado.")
        
        # Carrega o system prompt dinâmico do banco
        base_system_prompt = PromptService.get_system_prompt("NL2SQLAgent", NL2SQL_AGENT_SYSTEM_PROMPT)

        if trace:
            trace.log_thought("Assistente NL2SQL", "Combinando esquema com as regras de granularidade e instruções de uso.")

        # Constrói o contexto tabular detalhado
        schema_context = []
        for ds in datasets:
            table_info = {
                "sqlite_table": ds.get("sqlite_table"),
                "name": ds.get("name"),
                "granularity": ds.get("data_profile", {}).get("granularity_level", "UNKNOWN"),
                "columns": []
            }
            # Inclui instruções de uso analítico para guiar o SQL
            for col in ds.get("schema_json", {}).get("columns", []):
                table_info["columns"].append({
                    "name": col.get("name"),
                    "role": col.get("role"),
                    "can_group": col.get("grouping_suitability") == "HIGH",
                    "instruction": col.get("usage_instructions")
                })
            schema_context.append(table_info)

        prompt = f"""
Pergunta do Usuário: "{user_prompt}"

=== REGRAS DE NEGÓCIO ESPECIALIZADAS (Fórmulas do RAG/KB) ===
{specialist_context if specialist_context else "Nenhuma regra específica."}

=== SCHEMA DAS TABELAS E REGRAS DE USO ===
{json.dumps(schema_context, indent=2, ensure_ascii=False)}

=== RELACIONAMENTOS SEMÂNTICOS (DICAS DE JOIN) ===
{json.dumps(relationships, indent=2, ensure_ascii=False) if relationships else "Nenhum relacionamento formal."}

Gere o SQL respeitando as regras de granularidade e instruções acima.
        """
        
        try:
            # Tenta obter a resposta estruturada do Bedrock
            result = self.bedrock_service.invoke_with_json_output(
                system_prompt=base_system_prompt,
                user_message=prompt,
                temperature=0.1
            )
            
            if not result or not isinstance(result, dict):
                raise ValueError("Resposta do Bedrock não é um objeto JSON válido.")
            
            if trace:
                trace.log_thought("Assistente NL2SQL", f"Query estruturada com complexidade {result.get('complexity')}.")
                
            return {
                "specialist": "ASSISTENTE_NL2SQL",
                **result
            }
            
        except Exception as e:
            logger.error(f"[Assistente_NL2SQL] Falha na geração SQL: {e}")
            if trace:
                 trace.quick_log(trace.trace_id, trace.job_type, "Assistente NL2SQL: Erro", str(e), status="ERROR")
            return {
                "specialist": "ASSISTENTE_NL2SQL",
                "error": str(e),
                "sql": f"-- Erro na geração: {str(e)}",
                "description": "Falha crítica na orquestração LLM do assistente SQL."
            }
