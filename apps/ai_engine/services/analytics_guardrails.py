"""
apps.ai_engine.services.analytics_guardrails
Serviço de validação determinística para impedir erros analíticos comuns (ex: soma de idades).
"""
import logging
import re
import pandas as pd
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

class AnalyticsGuardrails:
    """
    Implementa verificações 'Hard Rules' que a LLM às vezes ignora.
    """
    
    # Colunas que NUNCA devem ser somadas ou ter média calculada
    PROHIBITED_AGGREGATION_KEYWORDS = [
        "idade", "age", "anos", "meses", "months", "years", 
        "id", "uuid", "pk", "key", "codigo", "cod_", "cpf", "cnpj",
        "sexo", "gender", "cep", "zipcode"
    ]

    @classmethod
    def validate_python_code(cls, code: str) -> Tuple[bool, str]:
        """
        Analisa o código Python em busca de operações proibidas.
        """
        # Procura por .sum() ou .mean() ou np.sum() etc em colunas proibidas
        for keyword in cls.PROHIBITED_AGGREGATION_KEYWORDS:
            # Regex para detectar agrupamento/soma que inclua keywords proibidas
            # Ex: df['idade'].sum() ou df.groupby('...')['idade'].mean()
            patterns = [
                rf"['\"]{keyword}['\"]\].sum\(\)",
                rf"['\"]{keyword}['\"]\].mean\(\)",
                rf"np\.(sum|mean)\(.*['\"]{keyword}['\"].*\)"
            ]
            for pattern in patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    msg = f"Operação estatística proibida detectada na coluna de perfil/identificação: '{keyword}'."
                    logger.warning(f"[Guardrails] {msg}")
                    return False, msg
        
        return True, ""

    @classmethod
    def validate_result_data(cls, data: Any, semantic_mapping: Dict[str, Any] = None) -> Tuple[bool, str]:
        """
        Valida o dicionário final de métricas/dados gerados pelo agente.
        """
        if not isinstance(data, dict):
            return True, ""

        metrics = data.get("metrics", {})
        if not isinstance(metrics, dict):
            return True, ""

        # Verifica se há valores absurdos (ex: soma de idades resultando em milhares)
        for key, value in metrics.items():
            key_lower = key.lower()
            if any(k in key_lower for k in ["idade", "age", "anos"]):
                if isinstance(value, (int, float)) and value > 150:
                    # Se o valor for > 150 e parecer uma soma (pelo nome da métrica)
                    if any(k in key_lower for k in ["soma", "total", "sum"]):
                        msg = f"Métrica suspeita detectada: '{key}' apresentou valor de {value}, sugerindo uma soma incorreta de idade."
                        return False, msg
        
        return True, ""

    @classmethod
    def identify_incorrect_measures(cls, column_mapping: Dict[str, Any]) -> List[str]:
        """
        Identifica colunas erroneamente classificadas como MEASURE.
        """
        fixes = []
        for col_name, info in column_mapping.items():
            name_lower = col_name.lower()
            if info.get("role") == "MEASURE":
                if any(k in name_lower for k in cls.PROHIBITED_AGGREGATION_KEYWORDS):
                    fixes.append(col_name)
        return fixes
