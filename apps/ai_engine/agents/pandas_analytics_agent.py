import json
import logging
from typing import Dict, Any, List

from django.conf import settings
from apps.ai_engine.services.bedrock_service import BedrockService
from apps.ai_engine.services.pandas_executor_service import PandasExecutorService

logger = logging.getLogger(__name__)

PANDAS_AGENT_SYSTEM_PROMPT = """Você é o Analista Quantitativo e Cientista de Dados Sênior da NTT DATA, especialista em Modelagem de Risco e Pandas.

Sua missão é transformar dados brutos em inteligência estratégica. Ao receber um dataset financeiro ou de crédito, você deve OBRIGATORIAMENTE realizar:

1. **ENGENHARIA DE ATRIBUTOS (Feature Engineering)**: 
   Não se limite às colunas originais. Crie NOVAS colunas que agreguem valor, como:
   - `score_credito`: Um score calculado (ex: 0 a 1000) baseado em variáveis de comportamento e renda.
   - `prob_default`: Probabilidade estimada de inadimplência (PD).
   - `rating_risco`: Classificação categórica (ex: Baixo, Médio, Alto, Crítico).
   - `comprometimento_renda`: % da renda comprometida com a dívida.

2. **ANÁLISE DE CARTEIRA COMPLETA**:
   - Calcule a 'Exposição Total' (EAD) somando os valores de toda a base.
   - Analise a 'Inadimplência Real' (% de atrasos sobre o total).
   - Distribua a carteira por faixas de Rating (Concentração de Risco).

3. **MODELAGEM ESTATÍSTICA**:
   Utilize `numpy` e `pandas` para correlações entre variáveis (ex: Idade vs Inadimplência) e aplique médias móveis ou regressões simples para projeções.

## Regras de Código:
- SEMPRE salve a tabela resultante enriquecida e os indicadores principais no dicionário de saída.
- O código deve ser robusto: trate valores nulos (`fillna`) antes de realizar cálculos matemáticos.
- Atribua o dicionário final (contendo 'metrics', 'summary' e 'chart_data') à variável GLOBAL 'result'.

IMPORTANTE: Siga rigorosamente as **REGRAS DE NEGÓCIO ESPECIALIZADAS** (Fórmulas do Especialista no contexto). Elas sobrepõem qualquer lógica padrão.
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

    def analyze(self, user_prompt: str, datasets_profiles: List[Dict[str, Any]] = None, max_rows: int = 5000, specialist_context: str = "", trace=None) -> Dict[str, Any]:
        """
        Executa o fluxo completo: Geração de Código -> Execução -> Síntese de Insight.
        """
        logger.info(f"[Assistente_Pandas] Iniciando fluxo de cálculo estatístico (Max Rows: {max_rows}).")
        
        if trace:
            trace.log_thought("Assistente Pandas", f"Iniciando análise de dados (limite de {max_rows} linhas) para identificar a melhor abordagem estatística.")

        # Prepara contexto de metadados para a LLM planejar o código
        metadata_context = []
        for ds in datasets_profiles or []:
            metadata_context.append({
                "name": ds.get("name"),
                "sqlite_table": ds.get("sqlite_table"),
                "profile": ds.get("data_profile", {})
            })

        # --- FASE 1: GERAÇÃO DE CÓDIGO ---
        planning_prompt = f"""
Pergunta do Usuário: "{user_prompt}"

=== REGRAS DE NEGÓCIO ESPECIALIZADAS (PRIORIDADE TOTAL) ===
{specialist_context if specialist_context else "Nenhuma regra de negócio externa informada. Use lógica estatística padrão."}

=== Metadados dos Datasets Disponíveis ===
{json.dumps(metadata_context, indent=2, ensure_ascii=False)}

Gere o código Python para realizar a análise estatística. Atribua o dicionário/valor final à variável 'result'.
        """
        
        try:
            plan = self.bedrock_service.invoke_with_json_output(
                system_prompt=PANDAS_AGENT_SYSTEM_PROMPT,
                user_message=planning_prompt,
                temperature=0.1
            )
            
            thought = plan.get("thought", "Planejando execução de código Pandas.")
            if trace:
                trace.log_thought("Assistente Pandas", f"Decidi realizar uma análise do tipo {plan.get('analysis_type')}: {thought}")

            code = plan.get("python_code")
            if not code:
                raise ValueError("O assistente não gerou código Python.")

            # --- FASE 2: EXECUÇÃO DO CÓDIGO ---
            logger.info(f"[Assistente_Pandas] Executando código de análise: {plan.get('analysis_type')}")
            if trace:
                trace.start_step("Assistente Pandas: Execução")
            
            exec_result = self.executor.execute_analysis(code, datasets_profiles, max_rows=max_rows)
            
            if trace:
                trace.end_step("Assistente Pandas: Execução", message=f"Cálculo matemático concluído via PandasExecutorService.", metadata={"code": code, "result_summary": str(exec_result["data"])[:200]})

            if exec_result["status"] != "success":
                return {
                    "specialist": "ASSISTENTE_PANDAS",
                    "error": exec_result.get("message"),
                    "analysis": "Houve um erro técnico ao processar os cálculos estatísticos solicitados."
                }

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
                "thought": plan.get("thought"),
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
