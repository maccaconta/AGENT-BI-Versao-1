"""
apps.datasets.services.athena_service
───────────────────────────────────────
Execução de queries analíticas via Amazon Athena.
"""
import logging
import time
from typing import Optional
import boto3
from botocore.exceptions import ClientError
from django.conf import settings

logger = logging.getLogger(__name__)


class AthenaQueryError(Exception):
    """Erro de execução de query Athena."""
    pass


class AthenaService:
    """Execução e gerenciamento de queries no Amazon Athena."""

    TERMINAL_STATES = {"SUCCEEDED", "FAILED", "CANCELLED"}
    POLL_INTERVAL = 2  # segundos entre checks

    def __init__(self):
        self.client = boto3.client("athena", region_name=settings.AWS_REGION)
        self.workgroup = settings.ATHENA_WORKGROUP
        self.output_location = settings.ATHENA_OUTPUT_LOCATION
        self.query_timeout = settings.ATHENA_QUERY_TIMEOUT

    def execute_query(
        self,
        sql: str,
        database: Optional[str] = None,
        wait: bool = True,
        timeout: Optional[int] = None,
    ) -> dict:
        """
        Executa query no Athena.

        Args:
            sql: Query SQL
            database: Database Glue (context)
            wait: Se True, aguarda conclusão sincronamente
            timeout: Timeout em segundos

        Returns:
            dict com query_execution_id, status, results (se wait=True)
        """
        timeout = timeout or self.query_timeout

        # Validação básica de segurança
        self._validate_sql(sql)

        try:
            start_params = {
                "QueryString": sql,
                "WorkGroup": self.workgroup,
                "ResultConfiguration": {
                    "OutputLocation": self.output_location,
                },
            }
            if database:
                start_params["QueryExecutionContext"] = {"Database": database}

            response = self.client.start_query_execution(**start_params)
            query_id = response["QueryExecutionId"]
            logger.info(f"Athena query iniciada: {query_id}")

            if not wait:
                return {"query_execution_id": query_id, "status": "RUNNING"}

            # Aguardar conclusão
            return self._wait_for_query(query_id, timeout)

        except ClientError as e:
            logger.error(f"Erro ao executar query Athena: {e}")
            raise AthenaQueryError(str(e)) from e

    def _wait_for_query(self, query_id: str, timeout: int) -> dict:
        """Aguarda conclusão da query com polling."""
        elapsed = 0
        while elapsed < timeout:
            status = self.get_query_status(query_id)
            state = status.get("state")

            if state in self.TERMINAL_STATES:
                if state != "SUCCEEDED":
                    error = status.get("state_change_reason", "Query falhou")
                    raise AthenaQueryError(f"Query {query_id} falhou: {error}")

                # Buscar resultados
                results = self.get_query_results(query_id)
                return {
                    "query_execution_id": query_id,
                    "status": state,
                    "results": results,
                    "statistics": status.get("statistics", {}),
                }

            time.sleep(self.POLL_INTERVAL)
            elapsed += self.POLL_INTERVAL

        raise AthenaQueryError(
            f"Timeout após {timeout}s para query {query_id}"
        )

    def get_query_status(self, query_id: str) -> dict:
        """Obtém status atual de uma query."""
        try:
            response = self.client.get_query_execution(
                QueryExecutionId=query_id
            )
            execution = response["QueryExecution"]
            status = execution.get("Status", {})
            stats = execution.get("Statistics", {})

            return {
                "query_execution_id": query_id,
                "state": status.get("State"),
                "state_change_reason": status.get("StateChangeReason"),
                "submission_time": status.get("SubmissionDateTime"),
                "completion_time": status.get("CompletionDateTime"),
                "statistics": {
                    "data_scanned_bytes": stats.get("DataScannedInBytes", 0),
                    "execution_time_ms": stats.get("TotalExecutionTimeInMillis", 0),
                },
            }
        except ClientError as e:
            logger.error(f"Erro ao obter status da query Athena: {e}")
            raise

    def get_query_results(
        self, query_id: str, max_rows: int = 10_000
    ) -> dict:
        """
        Obtém resultados de uma query concluída.

        Returns:
            {
                columns: [str],
                rows: [[str]],
                row_count: int,
                truncated: bool
            }
        """
        try:
            paginator = self.client.get_paginator("get_query_results")
            columns = []
            rows = []

            for i, page in enumerate(paginator.paginate(QueryExecutionId=query_id)):
                result_set = page["ResultSet"]

                # Primeira página tem o header
                if i == 0:
                    metadata = result_set.get("ResultSetMetadata", {})
                    col_info = metadata.get("ColumnInfo", [])
                    columns = [col["Name"] for col in col_info]

                    # Pular linha de header nos dados
                    data_rows = result_set.get("Rows", [])[1:]
                else:
                    data_rows = result_set.get("Rows", [])

                for row_data in data_rows:
                    row = [
                        datum.get("VarCharValue", "") if datum else ""
                        for datum in row_data.get("Data", [])
                    ]
                    rows.append(row)

                if len(rows) >= max_rows:
                    return {
                        "columns": columns,
                        "rows": rows[:max_rows],
                        "row_count": len(rows),
                        "truncated": True,
                    }

            return {
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "truncated": False,
            }

        except ClientError as e:
            logger.error(f"Erro ao obter resultados Athena: {e}")
            raise

    def get_sample_data(
        self,
        database: str,
        table: str,
        limit: int = 10,
    ) -> dict:
        """Obtém amostra de dados de uma tabela."""
        sql = f"SELECT * FROM `{database}`.`{table}` LIMIT {limit}"
        return self.execute_query(sql, database=database)

    def get_table_stats(self, database: str, table: str) -> dict:
        """Obtém estatísticas básicas de uma tabela."""
        sql = f"SELECT COUNT(*) as total FROM `{database}`.`{table}`"
        result = self.execute_query(sql, database=database)
        total = result["results"]["rows"][0][0] if result["results"]["rows"] else "0"
        return {"total_rows": int(total)}

    # ─── Security ─────────────────────────────────────────────────────────────

    FORBIDDEN_KEYWORDS = [
        "DROP ", "DELETE ", "INSERT ", "UPDATE ", "CREATE ",
        "ALTER ", "TRUNCATE ", "GRANT ", "REVOKE ", "EXEC ",
        "EXECUTE ", "--", "/*", "*/", "xp_", "sp_",
    ]

    def _validate_sql(self, sql: str) -> None:
        """
        Valida SQL para prevenir queries destrutivas.
        Athena é read-only por design, mas validamos como defesa em profundidade.
        """
        sql_upper = sql.upper().strip()
        for keyword in self.FORBIDDEN_KEYWORDS:
            if keyword in sql_upper:
                raise AthenaQueryError(
                    f"SQL contém keyword proibida: {keyword.strip()}"
                )
        if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
            raise AthenaQueryError(
                "Apenas queries SELECT ou WITH são permitidas."
            )
