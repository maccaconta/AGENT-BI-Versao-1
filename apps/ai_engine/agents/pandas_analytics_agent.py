import json
import logging
from typing import Dict, Any, List

from django.conf import settings
from apps.ai_engine.services.bedrock_service import BedrockService
from apps.ai_engine.services.pandas_executor_service import PandasExecutorService
from apps.ai_engine.services.prompt_service import PromptService

logger = logging.getLogger(__name__)

PANDAS_AGENT_SYSTEM_PROMPT = """Você é o Engenheiro Chefe de Analytics da NTT DATA. 
Sua missão é transformar dados brutos em DataFrames enriquecidos com KPIs de alta fidelidade estratégica.

## 🚫 REGRAS MANDATÓRIAS (ERRO ZERO):
- **CÁLCULOS PROIBIDOS**: NUNCA realize .sum() ou .mean() em colunas de perfil (Idade, IDs, CPFs). Use-as apenas em .groupby().
- **DNA DE RISCO**: Utilize obrigatoriamente as colunas marcadas como BALANCE, INCOME, LATE_DAYS e LIMIT para os cálculos abaixo.

## 📈 PROTOCOLO DE CONSTRUÇÃO DE FEATURES:
1. **Risco e Default**:
   - `default_flag`: 1 se LATE_DAYS > 15, senão 0.
   - `perc_inadimplencia`: (Soma do BALANCE de inadimplentes) / (Soma do BALANCE total).
2. **Feature Engineering (Adicione ao DataFrame)**:
   - `score_credito`: Baseado em atraso e comprometimento (ex: 1000 - (LATE_DAYS * 5) - (comprometimento * 2)).
   - `prob_default`: Escala 0 a 1.
   - `rating_risco`: Categorias (A, B, C, D, E).
   - `expected_loss`: PD * Exposure * LGD.

## ESTRUTURA DE RESPOSTA (JSON OBRIGATÓRIO):
Responda APENAS com um objeto JSON no seguinte formato:
{
  "analysis_type": "Tipo de análise (ex: Risco, Exposição, etc)",
  "thought": "Breve explicação do raciocínio estatístico",
  "python_code": "O código python completo aqui (use as regras abaixo)"
}

## REGRAS DE CÓDIGO (python_code):
- Use `pandas` e `numpy`.
- Atribua o dicionário com 'metrics', 'dataframe_processed' e 'insights' à variável GLOBAL 'result':
  result = {
    "metrics": { "kpi_nome": valor, ... },
    "dataframe_processed": df_com_novas_colunas,
    "insights": ["Insight quantitativo 1", ...]
  }
"""

PANDAS_SYNTHESIS_SYSTEM_PROMPT = """Você é o Diretor de Análise Estatística da NTT DATA. 
Sua tarefa é transformar resultados numéricos brutos em um relatório executivo de alto impacto.

- **Seja Assertivo**: Aponte exatamente onde o negócio está ganhando ou perdendo.
- **Contexto Financeiro**: Interprete correlações e anomalias sob a ótica de risco e retorno.
- **Linguagem Executiva**: Evite "economês" ou "tech-speak" excessivo; foque em insights acionáveis.
"""

class PandasAnalyticsAgent:
    """
    Assistente estatístico ativo que gera e executa código Pandas para análises complexas.
    """
    def __init__(self):
        self.bedrock_service = BedrockService()
        self.executor = PandasExecutorService()

    def analyze(self, user_prompt: str, datasets_metadata: List[Dict[str, Any]] = None, max_rows: int = 5000, specialist_context: str = "", risk_dna_context: Dict[str, Any] = None, feedback: str = "", trace=None) -> Dict[str, Any]:
        """
        Executa o fluxo completo: Geração de Código -> Execução -> Síntese de Insight.
        Suporta feedback corretivo para auto-ajuste.
        """
        logger.info(f"[Assistente_Pandas] Iniciando fluxo de cálculo estatístico (Max Rows: {max_rows}).")
        
        # Carrega o system prompt dinâmico do banco (Prioridade para regras administráveis)
        base_system_prompt = PromptService.get_system_prompt("PandasAnalyticsAgent", PANDAS_AGENT_SYSTEM_PROMPT)

        if trace:
            trace.log_thought("Assistente Pandas", f"Iniciando análise de dados (limite de {max_rows} linhas).")

        # Prepara contexto de metadados enriquecido
        metadata_context = []
        for ds in datasets_metadata or []:
            ds_context = {
                "name": ds.get("name"),
                "sqlite_table": ds.get("sqlite_table"),
                "granularity": ds.get("data_profile", {}).get("granularity_level", "UNKNOWN"),
                "columns": []
            }
            # Adiciona instruções de uso instruídas pela IA de Ingestão
            schema = ds.get("schema_json", {})
            if isinstance(schema, str):
                try: schema = json.loads(schema)
                except: schema = {}

            for col in schema.get("columns", []):
                ds_context["columns"].append({
                    "name": col.get("name"),
                    "role": col.get("role") or ("MEASURE" if col.get("is_value") else "DIMENSION"),
                    "can_group": col.get("grouping_suitability") == "HIGH",
                    "can_calculate": col.get("calculation_suitability") == "HIGH",
                    "instruction": col.get("usage_instructions", "")
                })
            metadata_context.append(ds_context)

        # --- FASE 1: GERAÇÃO DE CÓDIGO ---
        feedback_section = ""
        if feedback:
            feedback_section = f"\n\n🚨 ERROS NA TENTATIVA ANTERIOR (CORRIJA): {feedback}"

        planning_prompt = f"""
Pergunta do Usuário: "{user_prompt}"

=== METADADOS E REGRAS Analíticas POR COLUNA ===
{json.dumps(metadata_context, indent=2, ensure_ascii=False)}

=== REGRAS DE NEGÓCIO ESPECIALIZADAS (RAG/DOMAIN) ===
{specialist_context if specialist_context else "Nenhuma regra de negócio externa informada."}

=== MAPEAMENTO DE DNA DE RISCO ===
{json.dumps(risk_dna_context, indent=2, ensure_ascii=False) if risk_dna_context else "Nenhum mapeamento de DNA disponível."}
{feedback_section}

Gere o código Python. 
🚨 IMPORTANTE: Respeite as 'usage_instructions' e 'can_calculate' de cada coluna. Não realize agregados em colunas marcadas como 'can_calculate': false.
Decida se agrupamentos (groupby) são necessários para responder à pergunta com precisão executiva.
        """
        
        try:
            plan = self.bedrock_service.invoke_with_json_output(
                system_prompt=base_system_prompt,
                user_message=planning_prompt,
                temperature=0.1,
                max_tokens=2500
            )
            
            thought = plan.get("thought", "Planejando execução de código Pandas.")
            code = plan.get("python_code")
            if not code:
                raise ValueError("O assistente não gerou código Python.")

            if trace:
                trace.log_thought("Assistente Pandas", f"Decidi realizar uma análise do tipo {plan.get('analysis_type')}: {thought}")

            # --- FASE 2: EXECUÇÃO DO CÓDIGO ---
            logger.info(f"[Assistente_Pandas] Executando código de análise: {plan.get('analysis_type')}")
            if trace:
                trace.start_step("Assistente Pandas: Execução")
            
            # Determina se é análise de risco baseada na presença de DNA de risco
            is_risk_analysis = bool(risk_dna_context and any(risk_dna_context.values()))
            
            exec_result = self.executor.execute_analysis(
                code, 
                datasets_metadata, 
                max_rows=max_rows, 
                is_risk_analysis=is_risk_analysis
            )
            
            if exec_result["status"] != "success":
                if trace:
                    trace.end_step("Assistente Pandas: Execução", message=f"Falha na execução matemática: {exec_result.get('message')}", metadata={"code": code})
                return {
                    "specialist": "ASSISTENTE_PANDAS",
                    "error": exec_result.get("message"),
                    "python_code": code,
                    "thought": thought,
                    "analysis": "Houve um erro técnico ao processar os cálculos estatísticos solicitados."
                }

            if trace:
                result_peek = str(exec_result.get("data", ""))[:200]
                trace.end_step("Assistente Pandas: Execução", message=f"Cálculo matemático concluído via PandasExecutorService.", metadata={"code": code, "result_summary": result_peek})

            # --- FASE 3: SÍNTESE DO INSIGHT ---
            if trace:
                trace.log_thought("Assistente Pandas", "Interpretando os resultados numéricos para gerar um relatório executivo.")

            synthesis_prompt = f"""
Pergunta Original: "{user_prompt}"
Tipo de Análise: {plan.get('analysis_type')}
Raciocínio do Planejamento: {plan.get('thought')}

=== RESULTADO BRUTO DA EXECUÇÃO (Cálculo Real) ===
{json.dumps(exec_result["data"], indent=2, ensure_ascii=False)}

Escreva a análise final para o usuário.
            """
            
            final_report = self.bedrock_service.generate_text(
                prompt=synthesis_prompt,
                system_prompt=PANDAS_SYNTHESIS_SYSTEM_PROMPT,
                max_tokens=1500
            )
            
            return {
                "specialist": "ASSISTENTE_PANDAS",
                "analysis_type": plan.get("analysis_type"),
                "thought": thought,
                "python_code": code,
                "calculation_data": exec_result["data"],
                "analysis": final_report
            }
            
        except Exception as e:
            logger.error(f"[Assistente_Pandas] Falha crítica no fluxo: {e}")
            if trace:
                trace.quick_log(trace.trace_id, trace.job_type, "Assistente Pandas: Erro", str(e), status="ERROR")
            return {
                "specialist": "ASSISTENTE_PANDAS",
                "error": str(e),
                "analysis": "Não foi possível completar a análise estatística avançada."
            }
