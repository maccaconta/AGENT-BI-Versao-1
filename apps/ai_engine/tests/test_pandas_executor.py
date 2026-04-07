import unittest
import pandas as pd
import sqlite3
import os
from pathlib import Path
from django.test import TestCase
from django.conf import settings
from apps.ai_engine.services.pandas_executor_service import PandasExecutorService

class TestPandasExecutorService(TestCase):
    def setUp(self):
        self.executor = PandasExecutorService()
        self.db_path = self.executor.db_path
        
        # Garante que o diretório existe
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Cria uma tabela de teste no SQLite analítico
        conn = sqlite3.connect(self.db_path)
        df = pd.DataFrame({
            "id": [1, 2, 3, 4, 5],
            "score": [10, 20, 30, 40, 50],
            "inadimplencia": [0.1, 0.2, 0.3, 0.4, 0.5]
        })
        df.to_sql("test_dataset_12345678", conn, if_exists="replace", index=False)
        conn.close()

    def test_execute_correlation(self):
        datasets = [{"id": "12345678", "name": "test_dataset"}]
        code = """
df = dfs['test_dataset_12345678']
correlation = df['score'].corr(df['inadimplencia'])
result = {
    "correlation_value": correlation,
    "interpretation": "Correlação perfeita positiva encontrada."
}
        """
        response = self.executor.execute_analysis(code, datasets)
        
        self.assertEqual(response["status"], "success")
        self.assertAlmostEqual(response["data"]["correlation_value"], 1.0)
        self.assertEqual(response["data"]["interpretation"], "Correlação perfeita positiva encontrada.")

    def test_security_violation(self):
        # O executor ainda não bloqueia AUTOMATICAMENTE no execute_analysis (precisa chamar validate)
        # Mas vamos testar a lógica de validação que adicionamos
        safe_code = "result = 1 + 1"
        unsafe_code = "import os; os.system('echo hack')"
        
        self.assertTrue(self.executor.validate_code_safety(safe_code))
        self.assertFalse(self.executor.validate_code_safety(unsafe_code))

    def test_missing_result(self):
        datasets = [{"id": "12345678", "name": "test_dataset"}]
        code = "a = 1 + 1" # Não define a variável 'result'
        response = self.executor.execute_analysis(code, datasets)
        
        self.assertEqual(response["status"], "warning")
        self.assertIn("variável 'result' não foi definida", response["message"])
