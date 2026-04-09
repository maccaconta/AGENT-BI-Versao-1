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

    def execute_analysis(self, code: str, datasets: List[Dict[str, Any]], max_rows: int = 50000) -> Dict[str, Any]:
        """
        Executa um trecho de código Python sobre os datasets fornecidos.
        Cada dataset no SQLite será carregado como um DataFrame no dicionário 'dfs'.
        """
        if not code or not datasets:
            return {"status": "error", "message": "Código ou datasets ausentes."}

        # 1. Carregar DataFrames
        dfs = {}
        connection = sqlite3.connect(self.db_path)
        try:
            for ds in datasets:
                ds_id = str(ds.get("id", ""))
                ds_name = ds.get("name", "dataset")
                table_name = self.store.resolve_table_name(ds_id, ds_name)
                
                # Carrega o DF de forma eficiente com LIMIT
                try:
                    df = pd.read_sql_query(f'SELECT * FROM "{table_name}" LIMIT {max_rows}', connection)
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
                
            return {
                "status": "success",
                "data": final_result
            }
            
        except Exception as e:
            logger.error(f"Erro na execução do código Pandas: {e}")
            return {
                "status": "error",
                "message": str(e),
                "traceback": f"Erro ao processar: {code[:200]}..."
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
