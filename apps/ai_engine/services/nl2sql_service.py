"""
apps.ai_engine.services.nl2sql_service
Camada NL2SQL para propostas SQL auditaveis.
"""
from __future__ import annotations

import re
from typing import Any

class NL2SQLService:
    def build_sql_proposal(self, datasets: list[dict], semantic_relationships: list[dict]) -> dict:
        first_dataset = datasets[0] if datasets else {}
        table_name = self._pick_table_name(first_dataset)
        if not table_name:
            return self._insufficient_metadata()

        dataset_index = self._index_datasets(datasets)
        join_sql = self._build_join_count_sql(dataset_index, semantic_relationships or [])
        if join_sql:
            return join_sql

        grouped_sql = self._build_grouped_count_sql(first_dataset)
        if grouped_sql:
            return grouped_sql

        return {
            "description": "Consulta base auditavel para sintetizar o volume principal do dataset de referencia.",
            "sql": f'SELECT COUNT(*) AS total_registros FROM "{table_name}";',
        }

    def _build_join_count_sql(self, dataset_index: dict, semantic_relationships: list[dict]) -> dict | None:
        for rel in semantic_relationships:
            if not isinstance(rel, dict):
                continue

            source_dataset = self._resolve_dataset(rel, dataset_index, side="source")
            target_dataset = self._resolve_dataset(rel, dataset_index, side="target")
            if not source_dataset or not target_dataset:
                continue

            source_columns = self._collect_column_names(source_dataset)
            target_columns = self._collect_column_names(target_dataset)
            source_key = self._sanitize_identifier(rel.get("sourceKey") or rel.get("leftKey") or rel.get("source_key"))
            target_key = self._sanitize_identifier(rel.get("targetKey") or rel.get("rightKey") or rel.get("target_key"))
            if not source_key or not target_key:
                continue
            if source_key not in source_columns or target_key not in target_columns:
                continue

            source_table = self._pick_table_name(source_dataset)
            target_table = self._pick_table_name(target_dataset)
            if not source_table or not target_table:
                continue

            rel_type = str(rel.get("type") or rel.get("joinType") or "Inner").strip().lower()
            join_keyword = "LEFT JOIN" if rel_type == "left" else "INNER JOIN"
            return {
                "description": (
                    "Consulta auditavel baseada no relacionamento semantico informado para medir o volume integrado "
                    "entre fontes."
                ),
                "sql": (
                    f'SELECT COUNT(*) AS total_registros_integrados '
                    f'FROM "{source_table}" AS s {join_keyword} "{target_table}" AS t '
                    f'ON s."{source_key}" = t."{target_key}";'
                ),
            }
        return None

    def _build_grouped_count_sql(self, dataset: dict) -> dict | None:
        table_name = self._pick_table_name(dataset)
        if not table_name:
            return None

        # ── 1. Tentar usar data_profile para escolha inteligente de colunas ──
        data_profile = dataset.get("data_profile") or {}
        profile_cols = data_profile.get("columns") or {}

        if profile_cols:
            return self._build_sql_from_profile(table_name, profile_cols, dataset)

        # ── 2. Fallback: usar schema_json como antes ───────────────────────
        columns = self._collect_columns(dataset)
        if not columns:
            return None

        selected_cols = [self._sanitize_identifier(col) for col in (dataset.get("selectedCols") or []) if col]
        selected_cols = [col for col in selected_cols if col]
        text_like_cols = [col["name"] for col in columns if col["type"] in {"TEXT", "STRING"}]
        candidate_dimension = None

        if selected_cols:
            for col in selected_cols:
                if col in text_like_cols:
                    candidate_dimension = col
                    break
        elif text_like_cols:
            candidate_dimension = text_like_cols[0]

        if not candidate_dimension:
            return None

        return {
            "description": (
                "Consulta auditavel para distribuicao por dimensao do dataset de referencia, "
                "util para cards, graficos e tabela-resumo."
            ),
            "sql": (
                f'SELECT "{candidate_dimension}" AS dimensao, COUNT(*) AS total_registros '
                f'FROM "{table_name}" GROUP BY "{candidate_dimension}" '
                f'ORDER BY total_registros DESC LIMIT 20;'
            ),
        }

    def _build_sql_from_profile(self, table_name: str, profile_cols: dict, dataset: dict) -> dict | None:
        """
        Gera SQL enriquecida usando o data_profile:
        - Escolhe a coluna categórica com mais categorias únicas (melhor para GROUP BY)
        - Se houver coluna numérica, adiciona SUM() para métrica de negócio
        - Adiciona WHERE explorando os top valores mais relevantes como contexto
        """
        # Separar categóricas e numéricas pelo perfil
        categorical = [
            (col, info) for col, info in profile_cols.items()
            if info.get("type") == "categorical" and info.get("unique_count", 0) > 1
        ]
        numeric_cols = [
            col for col, info in profile_cols.items()
            if info.get("type") == "numeric"
        ]

        if not categorical:
            return None

        # Escolhe a categórica com mais categorias únicas (mas não ID-like: evita > 500 únicos)
        # Ideal: entre 2 e 200 valores distintos — perfeito para GROUP BY
        def cardinality_score(item):
            _, info = item
            u = info.get("unique_count", 0)
            if u < 2 or u > 500:
                return -1
            return u

        categorical.sort(key=cardinality_score, reverse=True)
        best_cat_col, best_cat_info = categorical[0]
        dim_col = self._sanitize_identifier(best_cat_col)
        if not dim_col:
            return None

        # Montar SELECT com métricas agregadas
        select_parts = [f'"{dim_col}" AS dimensao', "COUNT(*) AS total_registros"]
        measure_description = "contagem de registros"

        if numeric_cols:
            num_col = self._sanitize_identifier(numeric_cols[0])
            if num_col:
                select_parts.append(f'SUM("{num_col}") AS soma_{num_col}')
                select_parts.append(f'ROUND(AVG("{num_col}"), 2) AS media_{num_col}')
                measure_description = f"soma e media de {num_col} por {dim_col}"

        sql = (
            f'SELECT {chr(44).join(select_parts)} '
            f'FROM "{table_name}" '
            f'GROUP BY "{dim_col}" '
            f'ORDER BY total_registros DESC '
            f'LIMIT 20;'
        )

        # Enriquecer descricao com os top valores encontrados no perfil
        top_vals = best_cat_info.get("top_values") or []
        top_str = ", ".join([f'"{v["value"]}" ({v["pct"]}%)' for v in top_vals[:3]]) if top_vals else ""
        description = (
            f"Consulta auditavel agrupando por '{dim_col}' com {best_cat_info.get('unique_count')} "
            f"categorias distintas ({measure_description})."
            + (f" Principais categorias: {top_str}." if top_str else "")
        )

        return {"description": description, "sql": sql}

    def _index_datasets(self, datasets: list[dict]) -> dict:
        by_name = {}
        by_id = {}
        for dataset in datasets or []:
            if not isinstance(dataset, dict):
                continue
            dataset_name = str(dataset.get("name") or "").strip().lower()
            dataset_id = str(dataset.get("id") or "").strip().lower()
            if dataset_name:
                by_name[dataset_name] = dataset
            if dataset_id:
                by_id[dataset_id] = dataset
        return {"by_name": by_name, "by_id": by_id}

    def _resolve_dataset(self, rel: dict, dataset_index: dict, side: str) -> dict | None:
        name_keys = [side, f"{side}Name", f"{side}_name", f"{side}Dataset", f"{side}DatasetName"]
        id_keys = [f"{side}Id", f"{side}_id", f"{side}DatasetId"]

        for key in name_keys:
            value = rel.get(key)
            if value is None:
                continue
            normalized = str(value).strip().lower()
            if normalized and normalized in dataset_index["by_name"]:
                return dataset_index["by_name"][normalized]

        for key in id_keys:
            value = rel.get(key)
            if value is None:
                continue
            normalized = str(value).strip().lower()
            if normalized and normalized in dataset_index["by_id"]:
                return dataset_index["by_id"][normalized]
        return None

    def _collect_columns(self, dataset: dict) -> list[dict]:
        schema_columns = (dataset.get("schema_json") or {}).get("columns", [])
        schema_map: dict[str, str] = {}
        for column in schema_columns:
            if not isinstance(column, dict):
                continue
            column_name = self._sanitize_identifier(column.get("name"))
            if not column_name:
                continue
            schema_map[column_name] = self._normalize_type(column.get("type"))

        selected_cols = [self._sanitize_identifier(col) for col in (dataset.get("selectedCols") or []) if col]
        selected_cols = [col for col in selected_cols if col]
        if selected_cols:
            deduped_selected = []
            seen = set()
            for col in selected_cols:
                if col in seen:
                    continue
                seen.add(col)
                deduped_selected.append({
                    "name": col,
                    # Quando schema nao informa tipo para a coluna selecionada, assume-se TEXT
                    # sem inventar novos nomes de campo.
                    "type": schema_map.get(col, "TEXT"),
                })
            return deduped_selected

        if schema_map:
            return [{"name": key, "type": schema_map[key]} for key in schema_map]

        # Sem schema/selectedCols nao inferimos por amostra para evitar "inventar" colunas.
        return []

    def _collect_column_names(self, dataset: dict) -> set[str]:
        return {column["name"] for column in self._collect_columns(dataset)}

    def _normalize_type(self, value: Any) -> str:
        normalized = str(value or "").strip().lower()
        if any(token in normalized for token in ["int", "bigint", "smallint"]):
            return "INTEGER"
        if any(token in normalized for token in ["float", "double", "decimal", "number", "real"]):
            return "REAL"
        if "bool" in normalized:
            return "INTEGER"
        if any(token in normalized for token in ["date", "time"]):
            return "DATETIME"
        return "TEXT"

    def _pick_table_name(self, dataset: dict) -> str:
        if not isinstance(dataset, dict):
            return ""
        # Evitar "inventar" tabela por nome livre: usar apenas identificadores tabulares
        # explicitamente disponibilizados no contexto.
        for key in ["sqlite_table", "table_name", "glue_table"]:
            value = dataset.get(key)
            if value:
                return self._sanitize_identifier(value)
        return ""

    def _sanitize_identifier(self, value: Any) -> str:
        if value is None:
            return ""
        cleaned = re.sub(r"[^0-9a-zA-Z_]+", "_", str(value).strip())
        cleaned = re.sub(r"_+", "_", cleaned).strip("_").lower()
        if not cleaned:
            return ""
        if cleaned[0].isdigit():
            cleaned = f"t_{cleaned}"
        return cleaned

    def _insufficient_metadata(self) -> dict:
        return {
            "description": "Nao foi possivel gerar SQL auditavel sem metadados tabulares suficientes.",
            "sql": "/* Insufficient dataset metadata to build an auditable SQL query without inventing tables, columns or joins. */",
        }
