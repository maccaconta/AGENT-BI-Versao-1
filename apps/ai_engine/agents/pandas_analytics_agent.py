import json
import logging
from typing import Dict, Any, List

from django.conf import settings
from apps.ai_engine.services.bedrock_service import BedrockService

logger = logging.getLogger(__name__)

PANDAS_AGENT_SYSTEM_PROMPT = """Você é o Especialista Analítico / Agente de Data Science (Pandas) da NTT DATA - Agent-BI.
Sua missão é responder a perguntas matemáticas, estatísticas, preditivas ou analíticas avançadas baseando-se no perfilamento (Profiling) de dados estáticos pré-computados, gerados previamente.
Você NÃO executa código Python em tempo real, mas sim analisa as estatísticas (média, mediana, top frequências, valores nulos, correlações detectadas) presentes no dicionário de "data_profile" e retorna *insights* profundos.

- Mostre o diagnóstico, a tendência dos números e possíveis distorções baseadas nessas estatísticas.
- Construa uma resposta estruturada que possa ser incorporada aos *footerInsights* ou *applicationAnalysis*.
- Se a pergunta do usuário pedir para calcular exatamente algo que não está nos metadados de profiling, avise polidamente que sua capacidade atual utiliza métricas pré-computadas e indique que um analista de banco de dados poderia extrair via query exata.

Não forneça código executável, retorne estritamente o pensamento / resultado formatado para leitura humana do executivo.
"""

class PandasAnalyticsAgent:
    """
    Sub-Agente especializado em analisar os relatórios Numpy/Pandas já computados 
    (Data Profiling) para deduzir correlações ou responder dúvidas descritivas sem RCE.
    """
    def __init__(self):
        self.bedrock_service = BedrockService()

    def analyze(self, user_prompt: str, datasets_profile: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Gera a resposta analítica focada em estátistica descritiva.
        """
        logger.info("[Pandas_Agent] Analisando metadados estatísticos.")
        
        profile_json_str = json.dumps(datasets_profile, indent=2, ensure_ascii=False) if datasets_profile else "Nenhum perfil de dados disponível."
        
        prompt = f"""
Pergunta Analítica: "{user_prompt}"

=== Dados Estatísticos Pré-Computados (Pandas Profiling) ===
{profile_json_str}
============================================================

Com base EXCLUSIVAMENTE nas métricas acima, entregue sua análise avançada.
        """
        
        try:
            response_text = self.bedrock_service.generate_text(
                prompt=prompt,
                system_prompt=PANDAS_AGENT_SYSTEM_PROMPT,
                max_tokens=2000
            )
            
            return {
                "specialist": "PANDAS_AGENT",
                "analysis": response_text
            }
            
        except Exception as e:
            logger.error(f"[Pandas_Agent] Falha na análise: {e}")
            return {
                "specialist": "PANDAS_AGENT",
                "error": str(e),
                "analysis": "Não foi possível realizar a análise estatística avançada devido a um erro interno."
            }
