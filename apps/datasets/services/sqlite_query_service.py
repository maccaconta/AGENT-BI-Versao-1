"""
apps.datasets.services.sqlite_query_service
Executor SQLite somente leitura para o prototipo local.
"""
from __future__ import annotations

import re
import sqlite3
from decimal import Decimal
from typing import Any

from apps.datasets.services.sqlite_analytics_store import LocalSQLiteAnalyticsStoreService


class SQLiteQueryValidationError(Exception):
    """Erro de validacao ou execucao de SQL em modo local."""


class LocalSQLiteQueryService:
    MAX_ROWS = 200
    FORBIDDEN_SQL_PATTERNS = (
        r"\bINSERT\b",
        r"\bUPDATE\b",
        r"\bDELETE\b",
        r"\bDROP\b",
        r"\bALTER\b",
        r"\bCREATE\b",
        r"\bATTACH\b",
        r"\bDETACH\b",
        r"\bPRAGMA\b",
        r"\bREINDEX\b",
        r"\bVACUUM\b",
        r"\bTRUNCATE\b",
        r"\bREPLACE\b",
        r"\bMERGE\b",
        r"\bUPSERT\b",
    )

    def __init__(self):
        self.analytics_store = LocalSQLiteAnalyticsStoreService()

    def validate_read_only_sql(self, sql: str) -> str:
        normalized = (sql or "").strip()
        if not normalized:
            raise SQLiteQueryValidationError("SQL vazia.")

        compact = normalized.rstrip(";").strip()
        if not compact:
            raise SQLiteQueryValidationError("SQL vazia.")

        if ";" in compact:
            raise SQLiteQueryValidationError("Apenas uma instrucao SQL e permitida.")

        if not re.match(r"^(SELECT|WITH)\b", compact, flags=re.IGNORECASE):
            raise SQLiteQueryValidationError("Somente consultas SELECT ou WITH sao permitidas no prototipo local.")

        for pattern in self.FORBIDDEN_SQL_PATTERNS:
            if re.search(pattern, compact, flags=re.IGNORECASE):
                raise SQLiteQueryValidationError("A consulta contem comandos nao permitidos para execucao local.")

        return compact

    def execute_sql_for_datasets(self, datasets: list[dict], sql: str, limit: int | None = None) -> dict:
        validated_sql = self.validate_read_only_sql(sql)
        if not datasets:
            raise SQLiteQueryValidationError("Nenhum dataset foi fornecido para validacao local.")

        if self.analytics_store.has_all_tables(datasets):
            connection = sqlite3.connect(self.analytics_store.db_path)
            try:
                connection.row_factory = sqlite3.Row
                table_map = self._build_persisted_table_map(datasets)
                result = self._execute_sql(connection, validated_sql, limit)
                result["table_map"] = table_map
                result["engine"] = "sqlite-analytics-local"
                return result
            except sqlite3.Error as exc:
                raise SQLiteQueryValidationError(
                    f"Falha ao executar SQL no SQLite analitico local: {exc}"
                ) from exc
            finally:
                connection.close()

        connection = sqlite3.connect(":memory:")
        try:
            connection.row_factory = sqlite3.Row
            table_map = self._register_datasets(connection, datasets)
            result = self._execute_sql(connection, validated_sql, limit)
            result["table_map"] = table_map
            result["engine"] = "sqlite-local-inmemory-fallback"
            return result
        except sqlite3.Error as exc:
            raise SQLiteQueryValidationError(f"Falha ao executar SQL no SQLite local: {exc}") from exc
        finally:
            connection.close()

    def _execute_sql(self, connection: sqlite3.Connection, sql: str, limit: int | None) -> dict:
        cursor = connection.execute(sql)
        rows = cursor.fetchmany(limit or self.MAX_ROWS)
        columns = [item[0] for item in (cursor.description or [])]
        serialized_rows = [self._serialize_row(dict(row)) for row in rows]
        return {
            "validated_sql": sql,
            "columns": columns,
            "rows": serialized_rows,
            "row_count": len(serialized_rows),
        }

    def _build_persisted_table_map(self, datasets: list[dict]) -> dict[str, str]:
        table_map: dict[str, str] = {}
        for dataset in datasets or []:
            dataset_id = str(dataset.get("id") or "")
            dataset_name = dataset.get("name") or ""
            table_name = self.analytics_store.resolve_table_name(
                dataset_id=dataset_id,
                dataset_name=dataset_name,
            )
            if dataset_id:
                table_map[dataset_id] = table_name
            if dataset_name:
                table_map[str(dataset_name)] = table_name
        return table_map

    def _register_datasets(self, connection: sqlite3.Connection, datasets: list[dict]) -> dict[str, str]:
        table_map: dict[str, str] = {}
        for index, dataset in enumerate(datasets, start=1):
            table_name = self._pick_table_name(dataset, index)
            columns = self._collect_columns(dataset)
            if not columns:
                continue

            self._create_table(connection, table_name, columns)
            self._insert_rows(connection, table_name, columns, dataset.get("sample_json") or [])

            dataset_id = str(dataset.get("id") or table_name)
            table_map[dataset_id] = table_name
            dataset_name = dataset.get("name") or table_name
            table_map[dataset_name] = table_name
        return table_map

    def _pick_table_name(self, dataset: dict, index: int) -> str:
        candidates = [
            dataset.get("sqlite_table"),
            dataset.get("table_name"),
            dataset.get("glue_table"),
            dataset.get("name"),
            f"dataset_{index}",
        ]
        for candidate in candidates:
            if candidate:
                return self._sanitize_identifier(str(candidate))
        return f"dataset_{index}"

    def _collect_columns(self, dataset: dict) -> list[dict]:
        columns = []
        schema_columns = (dataset.get("schema_json") or {}).get("columns", [])
        for item in schema_columns:
            name = item.get("name")
            if not name:
                continue
            columns.append(
                {
                    "name": self._sanitize_identifier(str(name)),
                    "source_name": name,
                    "type": self._normalize_sqlite_type(item.get("type")),
                }
            )

        if columns:
            deduped = []
            seen = set()
            for column in columns:
                if column["name"] not in seen:
                    seen.add(column["name"])
                    deduped.append(column)
            return deduped

        sample_rows = dataset.get("sample_json") or []
        inferred = []
        for row in sample_rows[:10]:
            if isinstance(row, dict):
                for key, value in row.items():
                    safe_name = self._sanitize_identifier(str(key))
                    if safe_name not in {item["name"] for item in inferred}:
                        inferred.append(
                            {
                                "name": safe_name,
                                "source_name": key,
                                "type": self._infer_value_type(value),
                            }
                        )
        return inferred

    def _create_table(self, connection: sqlite3.Connection, table_name: str, columns: list[dict]) -> None:
        sql_columns = ", ".join(f'"{item["name"]}" {item["type"]}' for item in columns)
        connection.execute(f'CREATE TABLE "{table_name}" ({sql_columns})')

    def _insert_rows(
        self,
        connection: sqlite3.Connection,
        table_name: str,
        columns: list[dict],
        sample_rows: list[dict],
    ) -> None:
        if not sample_rows:
            return

        column_names = [item["name"] for item in columns]
        placeholders = ", ".join("?" for _ in column_names)
        quoted_columns = ", ".join(f'"{name}"' for name in column_names)
        values = []
        for row in sample_rows:
            if not isinstance(row, dict):
                continue
            values.append(
                [
                    self._coerce_value(row.get(item.get("source_name"), row.get(item["name"])))
                    for item in columns
                ]
            )

        if values:
            connection.executemany(
                f'INSERT INTO "{table_name}" ({quoted_columns}) VALUES ({placeholders})',
                values,
            )
            connection.commit()

    def _normalize_sqlite_type(self, field_type: Any) -> str:
        value = str(field_type or "").lower()
        if any(token in value for token in ["int", "bigint"]):
            return "INTEGER"
        if any(token in value for token in ["float", "double", "decimal", "number", "real"]):
            return "REAL"
        if "bool" in value:
            return "INTEGER"
        return "TEXT"

    def _infer_value_type(self, value: Any) -> str:
        if isinstance(value, bool):
            return "INTEGER"
        if isinstance(value, int):
            return "INTEGER"
        if isinstance(value, float):
            return "REAL"
        return "TEXT"

    def _coerce_value(self, value: Any) -> Any:
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float, str)) or value is None:
            return value
        return str(value)

    def _serialize_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {key: self._coerce_value(value) for key, value in row.items()}

    def _sanitize_identifier(self, value: str) -> str:
        cleaned = re.sub(r"[^0-9a-zA-Z_]+", "_", value.strip())
        cleaned = re.sub(r"_+", "_", cleaned).strip("_").lower()
        if not cleaned:
            cleaned = "dataset"
        if cleaned[0].isdigit():
            cleaned = f"t_{cleaned}"
        return cleaned
