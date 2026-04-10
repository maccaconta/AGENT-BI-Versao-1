import json
import logging
from typing import Dict, Any, List

from apps.ai_engine.services.bedrock_service import BedrockService
from apps.ai_engine.services.prompt_service import PromptService

logger = logging.getLogger(__name__)

DATA_INTERPRETER_SYSTEM_PROMPT = """Você é o Intérprete de Dados e Especialista Semântico da NTT DATA - Agent-BI.
Sua missão é dar alma e contexto de negócio aos dados brutos ingeridos, identificando a granularidade e as regras de uso analítico.

## 🧠 OBJETIVOS DE INTERPRETAÇÃO:

1. **MAPEAMENTO SEMÂNTICO (ANALYTIC ROLES)**: 
   Classifique cada coluna em (PRIMARY_KEY, DIMENSION, MEASURE, TIME, METADATA).
   - **DIMENSION**: Colunas categóricas ideais para quebras/agrupamentos (Segmentos, Status, Região).
   - **MEASURE**: Apenas valores financeiros ou transacionais aptos para cálculos aritméticos (Soma, Média).
   - **🚨 ALERTA DE PERFIL**: Idade, IDs, CPFs, CEPs e Scores nunca devem ser MEASURE. Eles são DIMENSION ou METADATA.

2. **DETECÇÃO DE GRANULARIDADE (LOWEST LEVEL)**:
   - Identifique se o dataset representa um **Snapshot/Cadastro** (Granularidade: INDIVIDUAL - Ex: Cadastro de Clientes) ou um **Histórico/Eventos** (Granularidade: HISTORICAL - Ex: Fato Mensal de Crédito).
   - Indique as colunas que formam a chave única.

3. **TAXONOMIA DE RISCO (DNA DOS DADOS)**:
   Identifique colunas cruciais para modelagem de risco usando os seguintes marcadores (`risk_dna_marker`):
   - `BALANCE`: Saldo devedor atual, principal em aberto.
   - `INCOME`: Renda mensal ou faturamento comprovado.
   - `LIMIT`: Limite de crédito total aprovado.
   - `LATE_DAYS`: Dias em atraso (DPD - Days Past Due).
   - `EXPOSURE`: Valor em risco na data base (EAD - Exposure at Default).
   - `PROBABILITY_OF_DEFAULT`: Percentual de probabilidade de inadimplência (PD).
   - `LOSS_GIVEN_DEFAULT`: Percentual de perda dado o default (LGD).
   - `RECOVERY`: Valores recuperados pós-default.
   - `COLLATERAL`: Valor de garantias (imóveis, veículos, CDBs).
   - `CREDIT_SCORE`: Pontuação quantitativa de crédito (Bureaus ou Interno).
   - `DEFAULT_FLAG`: Indicador binário de inadimplência (0 ou 1).

## Saída Exigida (JSON):
{
  "dataset_summary": "Resumo executivo do dataset...",
  "granularity_level": "INDIVIDUAL" | "HISTORICAL",
  "granularity_keys": ["col1", "col2"],
  "strategic_insights": ["Insight 1", ...],
  "column_mapping": {
    "nome_coluna": {
      "role": "PRIMARY_KEY" | "DIMENSION" | "MEASURE" | "TIME" | "METADATA",
      "business_description": "Descrição legível para o 'Dicionário de Negócio'",
      "grouping_suitability": "HIGH" | "MEDIUM" | "NONE",
      "calculation_suitability": "HIGH" | "LOW" | "NONE",
      "usage_instructions": "Diretrizes específicas de uso (ex: 'Usar para ponderação de PD')",
      "risk_dna_marker": "BALANCE" | "INCOME" | "LIMIT" | "LATE_DAYS" | "EXPOSURE" | "PD" | "LGD" | "COLLATERAL" | "SCORE" | "DEFAULT_FLAG" | null,
      "is_elected_for_risk": true | false
    }
  }
}
"""

class DataInterpreterAgent:
    """
    Agente responsável por dar inteligência semântica ao esquema de dados.
    """
    def __init__(self):
        self.bedrock_service = BedrockService()

    def interpret_schema(self, columns: List[Dict[str, Any]], sample_data: List[Dict[str, Any]], domain_name: str = "") -> Dict[str, Any]:
        """
        Analisa as colunas e dados para gerar o mapeamento semântico e instruções de uso.
        """
        logger.info(f"[Data_Interpreter] Iniciando interpretação estratégica. Domínio: {domain_name}")
        
        # Carrega o system prompt dinâmico se disponível no BD
        base_system_prompt = PromptService.get_system_prompt("DataInterpreterAgent", DATA_INTERPRETER_SYSTEM_PROMPT)
        
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
                temperature=0.1,
                max_tokens=2500
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
            
            # --- NOVO: Correção Pós-Inferência (Hard Rules) ---
            from apps.ai_engine.services.analytics_guardrails import AnalyticsGuardrails
            
            # Garante que temos um dicionário válido para evitar crash no loop
            if isinstance(llm_mapping, dict):
                incorrect_cols = AnalyticsGuardrails.identify_incorrect_measures(llm_mapping)
                for col in incorrect_cols:
                    logger.warning(f"[Data_Interpreter] Corrigindo classificação da coluna '{col}': MEASURE -> DIMENSION (Regra de Segurança).")
                    llm_mapping[col]["role"] = "DIMENSION"
                    llm_mapping[col]["reasoning"] += " [CORRIGIDO PELO GUARDRAIL: Impedir soma de idade/IDs]"
            else:
                logger.error("[Data_Interpreter] LLM retornou mapeamento em formato inválido (não-dicionário).")
                
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
            # 3. Métricas (Numéricos que não pareçam IDs nem Perfis)
            elif dtype in ["double", "float", "decimal", "int", "bigint", "long"]:
                # Proteção contra campos demográficos (Idade, Tempo) serem tratados como métricas somáveis
                demographic_keywords = ["idade", "age", "anos", "meses", "tempo", "months", "years", "sexo", "gender"]
                if role != "PRIMARY_KEY" and not any(k in name for k in demographic_keywords):
                   role = "MEASURE"
                   desc = f"Métrica: {desc}"
                else:
                   role = "DIMENSION"
                   desc = f"Perfil/Atributo: {desc}"
            
            # Identifica Marcadores de DNA de Risco (Elected Variables)
            risk_marker = None
            is_elected = False
            
            # Normaliza o nome para busca em keywords
            n = name.lower()
            
            # 1. Saldo / Exposição (BALANCE/EXPOSURE)
            if any(k in n for k in ["saldo", "balance_mes", "exp_total", "valor_devedor", "exposure", "ead", "vlr_dev"]):
                risk_marker = "BALANCE"
                is_elected = True
            # 2. Renda (INCOME)
            elif any(k in n for k in ["renda", "income", "salario", "faturamento", "receita_mensal"]):
                risk_marker = "INCOME"
                is_elected = True
            # 3. Atraso (LATE_DAYS)
            elif any(k in n for k in ["atraso", "late_days", "dias_vencido", "dpd", "overdue", "aging"]):
                risk_marker = "LATE_DAYS"
                is_elected = True
            # 4. Limite (LIMIT)
            elif any(k in n for k in ["limite", "limit_credito", "max_cap", "lim_aprovado"]):
                risk_marker = "LIMIT"
                is_elected = True
            # 5. Probabilidade de Default (PD)
            elif any(k in n for k in ["pd_", "probabilidade", "prob_default", "p_default"]):
                risk_marker = "PD"
                is_elected = True
            # 6. Perda dado o Default (LGD)
            elif any(k in n for k in ["lgd_", "loss_given", "perda_default"]):
                risk_marker = "LGD"
                is_elected = True
            # 7. Garantias (COLLATERAL)
            elif any(k in n for k in ["garantia", "collateral", "imovel_vlr", "veiculo_vlr", "ltv_"]):
                risk_marker = "COLLATERAL"
                is_elected = True
            # 8. Score de Crédito (SCORE)
            elif any(k in n for k in ["score", "rating", "pontuacao", "bureau", "serasa", "boavista"]):
                risk_marker = "SCORE"
                is_elected = True
            # 9. Recuperação (RECOVERY)
            elif any(k in n for k in ["recuperacao", "recovery", "vlr_pago_atraso"]):
                risk_marker = "RECOVERY"
                is_elected = True
            # 10. Default Flag (DEFAULT)
            elif any(k in n for k in ["flag_default", "is_default", "inadimplente", "bad_"]):
                risk_marker = "DEFAULT_FLAG"
                is_elected = True

            mapping[col.get("name")] = {
                "role": role,
                "business_description": desc,
                "risk_dna_marker": risk_marker,
                "is_elected_for_risk": is_elected,
                "reasoning": reason
            }
            print(f"   - [Heurística] {col.get('name')} -> {role} ({desc})")
            
        return mapping
