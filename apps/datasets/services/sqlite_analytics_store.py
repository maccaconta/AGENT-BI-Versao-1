"""
apps.datasets.services.sqlite_analytics_store
Persistencia analitica local em SQLite separado do banco administrativo.
"""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from django.conf import settings


def build_sqlite_table_name(dataset_id: str, dataset_name: str | None = None) -> str:
    """
    Gera nome de tabela estavel para o dataset no SQLite analitico local.
    """
    base = dataset_name or dataset_id or "dataset"
    safe_base = "".join(char.lower() if char.isalnum() else "_" for char in str(base))
    safe_base = "_".join(part for part in safe_base.split("_") if part) or "dataset"
    safe_suffix = "".join(char.lower() for char in str(dataset_id) if char.isalnum())[:8]
    return f"{safe_base}_{safe_suffix}" if safe_suffix else safe_base


class LocalSQLiteAnalyticsStoreService:
    """
    Mantem datasets ingeridos em um SQLite dedicado ao analytics local.
    """

    def __init__(self, db_path: str | None = None):
        self.db_path = Path(db_path or self._default_db_path())

    def upsert_dataset_rows(self, dataset, rows: list[dict], schema_json: dict | None = None) -> str:
        """
        Recria a tabela do dataset e grava as linhas no banco analitico local.
        """
        table_name = build_sqlite_table_name(str(dataset.id), getattr(dataset, "name", None))
        columns = self._collect_columns(schema_json=schema_json or {}, rows=rows or [])
        if not columns:
            raise ValueError("Nao foi possivel determinar colunas para tabela analitica local.")

        self._ensure_db_parent()
        connection = sqlite3.connect(self.db_path)
        try:
            self._ensure_registry_table(connection)
            self._drop_table(connection, table_name)
            self._create_table(connection, table_name, columns)
            self._insert_rows(connection, table_name, columns, rows or [])
            self._register_dataset(connection, dataset_id=str(dataset.id), table_name=table_name)
            connection.commit()
        finally:
            connection.close()
        return table_name

    def resolve_table_name(self, dataset_id: str, dataset_name: str | None = None) -> str:
        """
        Resolve a tabela preferindo o registro persistido; se nao houver, usa convencao.
        """
        candidate = build_sqlite_table_name(dataset_id, dataset_name)
        if not self.db_path.exists():
            return candidate

        connection = sqlite3.connect(self.db_path)
        try:
            self._ensure_registry_table(connection)
            row = connection.execute(
                'SELECT table_name FROM "__dataset_registry" WHERE dataset_id = ?',
                (dataset_id,),
            ).fetchone()
            if row and row[0]:
                return str(row[0])
            return candidate
        finally:
            connection.close()

    def has_all_tables(self, datasets: list[dict]) -> bool:
        if not self.db_path.exists():
            return False

        table_names = []
        for dataset in datasets or []:
            dataset_id = str(dataset.get("id") or "")
            dataset_name = str(dataset.get("name") or "")
            table_name = str(dataset.get("sqlite_table") or "").strip()
            if not table_name:
                table_name = self.resolve_table_name(dataset_id=dataset_id, dataset_name=dataset_name)
            if table_name:
                table_names.append(table_name)

        if not table_names:
            return False

        connection = sqlite3.connect(self.db_path)
        try:
            existing = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            return all(table_name in existing for table_name in table_names)
        finally:
            connection.close()

    def _default_db_path(self) -> str:
        configured = getattr(settings, "LOCAL_ANALYTICS_SQLITE_PATH", "")
        if configured:
            return str(configured)
        base_dir = Path(str(getattr(settings, "LOCAL_DATA_DIR", Path(settings.BASE_DIR) / "local_data")))
        return str(base_dir / "analytics" / "agent_bi_analytics.sqlite")

    def _ensure_db_parent(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _ensure_registry_table(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS "__dataset_registry" (
                dataset_id TEXT PRIMARY KEY,
                table_name TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

    def _register_dataset(self, connection: sqlite3.Connection, dataset_id: str, table_name: str) -> None:
        connection.execute(
            """
            INSERT INTO "__dataset_registry" (dataset_id, table_name, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(dataset_id) DO UPDATE SET
                table_name=excluded.table_name,
                updated_at=excluded.updated_at
            """,
            (dataset_id, table_name, datetime.now(timezone.utc).isoformat()),
        )

    def _drop_table(self, connection: sqlite3.Connection, table_name: str) -> None:
        connection.execute(f'DROP TABLE IF EXISTS "{table_name}"')

    def _create_table(self, connection: sqlite3.Connection, table_name: str, columns: list[dict]) -> None:
        sql_columns = ", ".join(f'"{item["name"]}" {item["type"]}' for item in columns)
        connection.execute(f'CREATE TABLE "{table_name}" ({sql_columns})')

    def _insert_rows(
        self,
        connection: sqlite3.Connection,
        table_name: str,
        columns: list[dict],
        rows: list[dict],
    ) -> None:
        if not rows:
            return
        column_names = [item["name"] for item in columns]
        placeholders = ", ".join("?" for _ in column_names)
        quoted_columns = ", ".join(f'"{name}"' for name in column_names)

        values = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            values.append(
                [
                    self._coerce_value(
                        row.get(item.get("source_name"), row.get(item["name"]))
                    )
                    for item in columns
                ]
            )

        if not values:
            return
        connection.executemany(
            f'INSERT INTO "{table_name}" ({quoted_columns}) VALUES ({placeholders})',
            values,
        )

    def _collect_columns(self, schema_json: dict, rows: list[dict]) -> list[dict]:
        columns = []
        schema_columns = (schema_json or {}).get("columns", []) if isinstance(schema_json, dict) else []
        for item in schema_columns:
            if not isinstance(item, dict):
                continue
            name = self._sanitize_identifier(item.get("name"))
            if not name:
                continue
            columns.append(
                {
                    "name": name,
                    "source_name": item.get("name"),
                    "type": self._normalize_sqlite_type(item.get("type")),
                }
            )

        if not columns:
            inferred = []
            seen = set()
            for row in rows[:50]:
                if not isinstance(row, dict):
                    continue
                for key, value in row.items():
                    column_name = self._sanitize_identifier(key)
                    if not column_name or column_name in seen:
                        continue
                    seen.add(column_name)
                    inferred.append(
                        {
                            "name": column_name,
                            "source_name": key,
                            "type": self._infer_value_type(value),
                        }
                    )
            columns = inferred

        deduped = []
        seen = set()
        for column in columns:
            name = column["name"]
            if name in seen:
                suffix = 2
                candidate = f"{name}_{suffix}"
                while candidate in seen:
                    suffix += 1
                    candidate = f"{name}_{suffix}"
                name = candidate
            seen.add(name)
            deduped.append(
                {
                    "name": name,
                    "source_name": column.get("source_name"),
                    "type": column["type"],
                }
            )
        return deduped

    def _normalize_sqlite_type(self, field_type: Any) -> str:
        value = str(field_type or "").lower()
        if any(token in value for token in ["int", "bigint", "smallint"]):
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
        if value is None:
            return None
        if isinstance(value, (bool, int, float, str)):
            return value
        if hasattr(value, "item") and callable(getattr(value, "item")):
            try:
                return value.item()
            except Exception:
                return str(value)
        return str(value)

    def _sanitize_identifier(self, value: Any) -> str:
        cleaned = re.sub(r"[^0-9a-zA-Z_]+", "_", str(value or "").strip())
        cleaned = re.sub(r"_+", "_", cleaned).strip("_").lower()
        if not cleaned:
            return ""
        if cleaned[0].isdigit():
            cleaned = f"t_{cleaned}"
        return cleaned
