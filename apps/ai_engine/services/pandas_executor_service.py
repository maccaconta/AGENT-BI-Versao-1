"""
apps.ai_engine.services.pandas_executor_service
Serviço para execução segura de código Pandas/Python sobre dados do SQLite analítico.
"""
import logging
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
from django.conf import settings
from apps.datasets.services.sqlite_analytics_store import LocalSQLiteAnalyticsStoreService
from apps.ai_engine.services.analytics_guardrails import AnalyticsGuardrails

logger = logging.getLogger(__name__)

class PandasExecutorError(Exception):
    """Erro na execução do código Pandas."""
    pass

class PandasExecutorService:
    """
    Executor de código Python especializado em análise de dados com Pandas.
    Focado em rodar estatísticas e cálculos avançados (correlação, tendência, anomalia).
    """
    
    def __init__(self):
        self.store = LocalSQLiteAnalyticsStoreService()
        self.db_path = self.store.db_path

    def execute_analysis(self, code: str, datasets: List[Dict[str, Any]], max_rows: int = 50000, is_risk_analysis: bool = False) -> Dict[str, Any]:
        """
        Executa um trecho de código Python sobre os datasets fornecidos.
        Cada dataset no SQLite será carregado como um DataFrame no dicionário 'dfs'.
        
        Args:
            is_risk_analysis: Se True, remove LIMIT para análise completa da carteira (integridade estatística)
        """
        if not code or not datasets:
            return {"status": "error", "message": "Código ou datasets ausentes."}

        # 0. Validação de Guardrails (Código)
        is_safe, error_msg = AnalyticsGuardrails.validate_python_code(code)
        if not is_safe:
            return {"status": "error", "message": f"Bloqueio de Segurança Analítica: {error_msg}"}

        # 1. Carregar DataFrames
        dfs = {}
        connection = sqlite3.connect(self.db_path)
        try:
            for ds in datasets:
                ds_id = str(ds.get("id", ""))
                ds_name = ds.get("name", "dataset")
                table_name = self.store.resolve_table_name(ds_id, ds_name)
                
                # Para análise de risco, carrega TODOS os dados (sem LIMIT) para integridade estatística
                # Contrário ao design anterior que aplicava LIMIT sempre
                if is_risk_analysis:
                    query = f'SELECT * FROM "{table_name}"'
                    logger.info(f"Carregando dataset completo para análise de risco: {table_name}")
                else:
                    query = f'SELECT * FROM "{table_name}" LIMIT {max_rows}'
                
                try:
                    df = pd.read_sql_query(query, connection)
                    # Adiciona ao dicionário de execução com nome amigável e original
                    # Adiciona ao dicionário de execução com nome amigável e original
                    dfs[table_name] = df
                    safe_name = "".join(c if c.isalnum() else "_" for c in ds_name).lower()
                    dfs[safe_name] = df
                except Exception as e:
                    logger.warning(f"Falha ao carregar tabela {table_name}: {e}")
        finally:
            connection.close()

        if not dfs:
            return {"status": "error", "message": "Nenhum dado pôde ser carregado do SQLite analítico."}

        # 2. Preparar ambiente de execução (Restrito)
        # O agente deve colocar o resultado final na variável 'result'
        exec_globals = {
            "pd": pd,
            "np": np,
            "dfs": dfs,
            "result": None,
            "print": logger.info # Redireciona prints para o log
        }
        
        # 3. Execução Protegida
        try:
            # Remove imports perigosos do escopo se houverem
            # (O ideal é usar um sandbox real, mas aqui aplicamos restrições de namespace)
            exec(code, exec_globals)
            
            final_result = exec_globals.get("result")
            
            if final_result is None:
                return {
                    "status": "warning",
                    "message": "Código executado, mas a variável 'result' não foi definida.",
                    "data": None
                }
            
            # Validação obrigatória para análise de risco: verificar features criadas
            if is_risk_analysis:
                validation_result = self._validate_risk_features(final_result)
                if not validation_result["valid"]:
                    logger.warning(f"Análise de risco incompleta: {validation_result['missing_features']}")
                    return {
                        "status": "error",
                        "message": f"Análise de risco incompleta. Features obrigatórias ausentes: {', '.join(validation_result['missing_features'])}",
                        "data": final_result
                    }
                
            # Validação de Guardrails (Dados)
            is_valid_data, data_error = AnalyticsGuardrails.validate_result_data(final_result)
            if not is_valid_data:
                return {"status": "error", "message": f"Dados Inválidos Detectados: {data_error}", "data": None}

            return {
                "status": "success",
                "data": final_result
            }
            
        except Exception as e:
            logger.error(f"Erro na execução do código Pandas: {e}")
            return {
                "status": "error",
                "message": str(e),
                "traceback": f"Erro ao processar: {code[:200]}...",
                "data": None
            }

    def validate_code_safety(self, code: str) -> bool:
        """
        Verificação básica de segurança para evitar RCE malicioso.
        """
        forbidden = ["import os", "import subprocess", "import sys", "eval(", "exec(", "open(", "pickle"]
        for word in forbidden:
            if word in code:
                return False
        return True

    def _validate_risk_features(self, result: Any) -> Dict[str, Any]:
        """
        Valida se a análise de risco criou as features obrigatórias.
        Retorna dict com 'valid': bool e 'missing_features': list
        """
        required_features = ["score_credito", "prob_default", "rating_risco"]
        missing_features = []
        
        # Se o resultado é um DataFrame, verifica se as colunas foram criadas
        if isinstance(result, pd.DataFrame):
            existing_columns = [col.lower() for col in result.columns]
            for feature in required_features:
                if feature.lower() not in existing_columns:
                    # Verifica variações comuns
                    variations = [feature, feature.replace("_", ""), f"prob_{feature}", f"{feature}_calc"]
                    if not any(var.lower() in existing_columns for var in variations):
                        missing_features.append(feature)
        
        # Se é um dict, verifica se contém as métricas
        elif isinstance(result, dict):
            result_keys = [key.lower() for key in result.keys()]
            for feature in required_features:
                if feature.lower() not in result_keys:
                    missing_features.append(feature)
        
        return {
            "valid": len(missing_features) == 0,
            "missing_features": missing_features
        }

    def materialize_dataframe(self, df: pd.DataFrame, table_name: str) -> bool:
        """
        Persiste um DataFrame em uma tabela no SQLite analítico.
        Útil para 'congelar' resultados de cálculos complexos.
        """
        if not isinstance(df, pd.DataFrame):
            logger.error(f"Tentativa de materializar objeto que não é DataFrame: {type(df)}")
            return False
            
        connection = sqlite3.connect(self.db_path)
        try:
            logger.info(f"Materializando resultados na tabela: {table_name} ({len(df)} linhas)")
            df.to_sql(table_name, connection, if_exists='replace', index=False)
            return True
        except Exception as e:
            logger.error(f"Falha ao materializar DataFrame em {table_name}: {e}")
            return False
        finally:
            connection.close()
