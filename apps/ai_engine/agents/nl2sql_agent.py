"""
apps.ai_engine.agents.nl2sql_agent
Agente especialista em geração de SQL complexo (Joins, CTEs, Window Functions) via LLM.
"""
import json
import logging
from typing import Dict, Any, List

from apps.ai_engine.services.bedrock_service import BedrockService

logger = logging.getLogger(__name__)

NL2SQL_AGENT_SYSTEM_PROMPT = """Você é o Analista Financeiro Sênior e Especialista em SQL (NL2SQL) da NTT DATA - Agent-BI.
Sua missão é converter perguntas de usuários em consultas SQL estratégicas que forneçam uma visão analítica completa do negócio.

Ao receber uma pergunta, você não deve ser apenas um executor técnico, mas um parceiro de negócios que busca:
1. **Visão de Ranking**: Para pedidos de "maior", "melhor" ou "pior", retorne SEMPRE uma lista (ex: Top 10) e não apenas o primeiro registro. Isso permite ao usuário ver a distribuição.
2. **Visão de Evolução**: Se houver colunas de data/tempo, inclua-as na query para permitir análises de tendência e sazonalidade, mesmo que o usuário não peça explicitamente a data.
3. **Visão de Contexto**: Traga dimensões descritivas (ex: Categoria, Região, Status) que ajudem a explicar o "porquê" por trás dos números.

## Regras Técnicas (SQLite):
- Gere uma única instrução SQL (SELECT ou WITH) robusta.
- Use APENAS as tabelas e colunas explicitamente fornecidas no contexto.
- Utilize os relacionamentos semânticos fornecidos para realizar JOINs precisos.
- Use CTEs ou Window Functions para cálculos complexos de ranking ou acumulados.
- NUNCA gere instruções destrutivas (INSERT, UPDATE, DELETE, DROP).

## Saída Exigida (JSON):
Retorne estritamente um JSON válido com os campos:
{
  "sql": "A consulta SQL gerada",
  "description": "Uma explicação concisa voltada para o negócio (ex: 'Listando os 10 clientes com maior risco para análise de exposição')",
  "tables_used": ["lista", "de", "tabelas"],
  "complexity": "LOW" | "MEDIUM" | "HIGH"
}
"""

class NL2SQLAgent:
    """
    Assistente especializado em traduzir linguagem natural para SQL complexo 
    usando o poder do LLM Bedrock, indo além das heurísticas básicas.
    """
    def __init__(self):
        self.bedrock_service = BedrockService()

    def generate_sql(self, user_prompt: str, datasets: List[Dict[str, Any]], relationships: List[Dict[str, Any]] = None, trace=None) -> Dict[str, Any]:
        """
        Gera a proposta SQL baseada no contexto tabular.
        """
        logger.info("[Assistente_NL2SQL] Iniciando geração de SQL complexa.")
        
        if trace:
            trace.log_thought("Assistente NL2SQL", "Analisando o esquema das tabelas e os relacionamentos para construir a query ideal.")

        # Constrói o contexto tabular detalhado
        schema_context = []
        for ds in datasets:
            table_info = {
                "sqlite_table": ds.get("sqlite_table"),
                "name": ds.get("name"),
                "description": ds.get("description"),
                "columns": ds.get("schema_json", {}).get("columns", []) or ds.get("data_profile", {}).get("columns", [])
            }
            schema_context.append(table_info)

        prompt = f"""
Pergunta do Usuário: "{user_prompt}"

=== SCHEMA DAS TABELAS DISPONÍVEIS ===
{json.dumps(schema_context, indent=2, ensure_ascii=False)}

=== RELACIONAMENTOS SEMÂNTICOS (DICAS DE JOIN) ===
{json.dumps(relationships, indent=2, ensure_ascii=False) if relationships else "Nenhum relacionamento formal informado."}

Gere a SQL proposta abaixo seguindo as regras do sistema.
        """
        
        try:
            # Tenta obter a resposta estruturada do Bedrock
            result = self.bedrock_service.invoke_with_json_output(
                system_prompt=NL2SQL_AGENT_SYSTEM_PROMPT,
                user_message=prompt,
                temperature=0.1
            )
            
            if not result or not isinstance(result, dict):
                raise ValueError("Resposta do Bedrock não é um objeto JSON válido.")
            
            if trace:
                trace.log_thought("Assistente NL2SQL", f"Query estruturada com complexidade {result.get('complexity')}. Tabelas afetadas: {', '.join(result.get('tables_used', []))}")
                
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
