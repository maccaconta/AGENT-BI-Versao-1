import json
import logging
from typing import Dict, Any, List

from django.conf import settings
from apps.ai_engine.services.bedrock_service import BedrockService
from apps.ai_engine.services.pandas_executor_service import PandasExecutorService

logger = logging.getLogger(__name__)

PANDAS_AGENT_SYSTEM_PROMPT = """Você é o Analista Estatístico e Financeiro Sênior da NTT DATA - Agent-BI, especialista em Pandas.
Sua missão é realizar análises profundas que revelem a saúde financeira e operacional através dos dados.

Ao planejar seu código Python, pense como um analista que busca:
1. **Padrões e Tendências**: Não calcule apenas médias simples; busque variações no tempo, taxas de crescimento e médias móveis.
2. **Distribuição e Risco**: Para análises de risco, identifique a concentração (ex: 80/20), desvios padrão e outliers que representam ameaças ou oportunidades.
3. **Visão de Conjunto**: Se o usuário pedir um ranking, o resultado deve conter múltiplos registros (Top 10) para análise comparativa.
4. **Projeção e Futuro**: Para perguntas sobre "valor futuro" ou "tendência futura", utilize modelos simples de regressão ou extrapolação (ex: `np.polyfit` ou médias móveis).

## Regras de Código:
- Utilize o dicionário 'dfs' (ex: dfs['tabela']).
- Atribua o dicionário/lista final de resultados à variável GLOBAL 'result'.
- O código deve ser focado em performance e segurança.

## Saída Exigida (JSON):
{
  "thought": "Seu raciocínio analítico sobre quais indicadores, correlações ou projeções serão extraídos",
  "python_code": "O código para execução",
  "analysis_type": "CORRELATION" | "ANOMALY" | "TREND" | "DESCRIPTIVE" | "PREDICTION"
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

    def analyze(self, user_prompt: str, datasets: List[Dict[str, Any]] = None, trace=None) -> Dict[str, Any]:
        """
        Executa o fluxo completo: Geração de Código -> Execução -> Síntese de Insight.
        """
        logger.info("[Assistente_Pandas] Iniciando fluxo de cálculo estatístico.")
        
        if trace:
            trace.log_thought("Assistente Pandas", "Iniciando análise de dados para identificar a melhor abordagem estatística.")

        # Prepara contexto de metadados para a LLM planejar o código
        metadata_context = []
        for ds in datasets:
            metadata_context.append({
                "name": ds.get("name"),
                "sqlite_table": ds.get("sqlite_table"),
                "profile": ds.get("data_profile", {})
            })

        # --- FASE 1: GERAÇÃO DE CÓDIGO ---
        planning_prompt = f"""
Pergunta do Usuário: "{user_prompt}"

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
            
            exec_result = self.executor.execute_analysis(code, datasets)
            
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
