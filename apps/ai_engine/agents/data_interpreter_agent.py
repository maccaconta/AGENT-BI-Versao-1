import json
import logging
from typing import Dict, Any, List

from apps.ai_engine.services.bedrock_service import BedrockService

logger = logging.getLogger(__name__)

DATA_INTERPRETER_SYSTEM_PROMPT = """Você é o Intérprete de Dados e Especialista Semântico da NTT DATA - Agent-BI.
Sua missão é dar alma e contexto de negócio aos dados brutos ingeridos. 

Ao analisar o esquema e a amostra de dados, você deve gerar:

1. **MAPEAMENTO SEMÂNTICO DE COLUNAS**: 
   Classifique cada coluna em (PRIMARY_KEY, DIMENSION, MEASURE, TIME, METADATA) e sugira uma "Descrição de Negócio" legível (ex: traduzir termos técnicos como "cli_sl" para "Saldo do Cliente"). Se for uma data, tente identificar o formato (ex: DD/MM/YYYY).

2. **RESUMO EXECUTIVO (DATASET SUMMARY)**: 
   Um parágrafo de impacto para o C-Level explicando o que este dataset representa para a instituição (ex: "Este dataset contém a visão histórica dos últimos 24 meses de inadimplência da carteira de crédito PF").

3. **DETECÇÃO DE TABELA FATO (FACT TABLE)**:
   Identifique se o dataset é uma "Tabela Fato" (histórico de eventos). Uma tabela fato tradicional costuma ter chaves compostas que individualizam a linha: um identificador (ID, Código, CPF) + um marcador temporal (Data, Ano/Mês).

4. **INSIGHTS ESTRATÉGICOS (USE CASES)**: 
   Uma lista de até 5 casos de uso de como o banco pode usar esses dados para melhorar resultados ou mitigar riscos.

## Saída Exigida (JSON):
{
  "dataset_summary": "Resumo executivo do dataset...",
  "is_fact_table": true,
  "is_fact_table_reasoning": "Raciocínio para classificar como Fato ou Dimensão/Cadastro",
  "strategic_insights": ["Insight 1", "Insight 2", ...],
  "column_mapping": {
    "nome_coluna": {
      "role": "PRIMARY_KEY" | "DIMENSION" | "MEASURE" | "TIME" | "METADATA",
      "business_description": "Descrição legível para humanos...",
      "date_format_hint": "YYYY-MM-DD" | null,
      "reasoning": "Porquê desta classificação"
    }
  }
}
"""

class DataInterpreterAgent:
    """
    Agente responsável por dar inteligência semântica ao esquema de dados, 
    ajudando os outros agentes a não cometerem erros primários como agrupar por IDs.
    """
    def __init__(self):
        self.bedrock_service = BedrockService()

    def interpret_schema(self, columns: List[Dict[str, Any]], sample_data: List[Dict[str, Any]], domain_name: str = "") -> Dict[str, Any]:
        """
        Analisa as colunas e dados para gerar o mapeamento semântico, resumo e insights.
        Respeita marcações manuais (is_key, is_historical_date, etc.) se presentes no schema.
        """
        logger.info(f"[Data_Interpreter] Iniciando interpretação semântica e estratégica. Domínio: {domain_name}")
        
        specialist_context = ""
        if domain_name:
            try:
                from apps.shared_models import PromptTemplate
                # Busca na biblioteca de templates de prompt (SPECIALIST)
                specialist_template = PromptTemplate.objects.filter(
                    name__icontains=domain_name,
                    category="SPECIALIST"
                ).first()
                if specialist_template:
                    specialist_context = f"\n\nCONTEXTO DO ESPECIALISTA DE DOMÍNIO:\n{specialist_template.content}\n"
                    logger.info(f"[Data_Interpreter] Especialista aplicado: {specialist_template.name}")
            except Exception as e:
                logger.warning(f"[Data_Interpreter] Erro ao carregar especialista: {e}")

        system_prompt = DATA_INTERPRETER_SYSTEM_PROMPT + specialist_context
        
        manual_overrides = {}
        columns_to_infer = []
        
        # 1. Identifica Overrides Manuais
        for col in columns:
            col_name = col.get("name")
            role = None
            if col.get("is_key"): role = "PRIMARY_KEY"
            elif col.get("is_historical_date"): role = "TIME"
            elif col.get("is_category"): role = "DIMENSION"
            elif col.get("is_value"): role = "MEASURE"
            
            if role:
                manual_overrides[col_name] = {
                    "role": role,
                    "business_description": col.get("description", ""),
                    "reasoning": "Definição manual do usuário (Governança)."
                }
            else:
                columns_to_infer.append(col)

        # 2. Invocação Bedrock
        prompt = f"""
=== SCHEMA DAS COLUNAS PARA ANÁLISE ===
{json.dumps(columns_to_infer, indent=2, ensure_ascii=False)}

=== AMOSTRA DE DADOS (TOP 10) ===
{json.dumps(sample_data, indent=2, ensure_ascii=False)}

Gere o mapeamento semântico, o resumo estratégico e a descrição de negócio seguindo as regras do sistema.
"""
        
        try:
            print(f"[Data_Interpreter] 📡 Solicitando inteligência ao Amazon Bedrock (Contexto: {domain_name or 'Geral'})...")
            result = self.bedrock_service.invoke_with_json_output(
                system_prompt=system_prompt,
                user_message=prompt,
                temperature=0
            )
            
            if not result or "column_mapping" not in result:
                print("[Data_Interpreter] ⚠️ Resposta inválida da LLM. Ativando Heurística Local.")
                heuristic_mapping = self._heuristic_fallback(columns_to_infer, sample_data)
                result = {
                    "column_mapping": heuristic_mapping,
                    "dataset_summary": "Processamento local (Heurística).",
                    "strategic_insights": ["Análise semântica simplificada aplicada localmente."]
                }
                
            # Mescla overrides manuais com inferência da LLM (Overrides ganham)
            llm_mapping = result.get("column_mapping", {})
            for col_name, override in manual_overrides.items():
                llm_mapping[col_name] = override
                
            result["column_mapping"] = llm_mapping
            logger.info(f"[Data_Interpreter] Análise estratégica concluída para {len(llm_mapping)} colunas.")
            return result
            
        except Exception as e:
            print(f"[Data_Interpreter] ❌ Falha na interpretação IA ({e}). Ativando Heurística Local.")
            heuristic_mapping = self._heuristic_fallback(columns_to_infer, sample_data)
            
            # Mescla overrides
            for col_name, override in manual_overrides.items():
                heuristic_mapping[col_name] = override

            return {
                "column_mapping": heuristic_mapping,
                "dataset_summary": "Dataset processado via Heurística de Emergência (Zero-Infra).",
                "strategic_insights": ["Identificação automática de campos baseada em padrões de nomenclatura."],
                "error": str(e)
            }

    def _heuristic_fallback(self, columns: List[Dict[str, Any]], sample: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Lógica determinística para não deixar o usuário na mão caso a IA falhe.
        """
        mapping = {}
        for col in columns:
            name = col.get("name", "").lower()
            dtype = col.get("type", "").lower()
            
            role = "DIMENSION"
            desc = name.replace("_", " ").title()
            reason = "Classificação por padrão de nome/tipo."
            
            # 1. Chaves
            if any(k in name for k in ["id", "uuid", "pk", "key", "codigo", "cod_"]):
                role = "PRIMARY_KEY"
                desc = f"Identificador: {desc}"
            # 2. Tempo
            elif any(k in name for k in ["data", "date", "dt_", "time", "created", "update", "inicio", "fim"]):
                role = "TIME"
                desc = f"Data/Hora: {desc}"
            # 3. Métricas (Numéricos que não pareçam IDs)
            elif dtype in ["double", "float", "decimal", "int", "bigint", "long"]:
                if role != "PRIMARY_KEY":
                   role = "MEASURE"
                   desc = f"Métrica: {desc}"
            
            mapping[col.get("name")] = {
                "role": role,
                "business_description": desc,
                "reasoning": reason
            }
            print(f"   - [Heurística] {col.get('name')} -> {role} ({desc})")
            
        return mapping
