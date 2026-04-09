"""
apps.datasets.services.parquet_service
────────────────────────────────────────
Conversão CSV/XLSX → Parquet otimizado + inferência de schema.
"""
import io
import logging
from typing import Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from django.conf import settings

logger = logging.getLogger(__name__)


class ParquetService:
    """
    Converte CSV/XLSX para formato Parquet otimizado
    com particionamento e compressão.
    """

    DEFAULT_COMPRESSION = "snappy"
    MAX_ROWS = settings.MAX_FILE_ROWS

    def convert_csv_to_parquet(
        self,
        csv_bytes: bytes,
        encoding: str = "utf-8",
        delimiter: str = ",",
    ) -> tuple[bytes, dict]:
        """
        Converte CSV para Parquet.
        Retorna (parquet_bytes, schema_info).
        """
        try:
            df = pd.read_csv(
                io.BytesIO(csv_bytes),
                encoding=encoding,
                sep=delimiter,
                low_memory=False,
                nrows=self.MAX_ROWS,
            )
            return self._dataframe_to_parquet(df)
        except Exception as e:
            logger.error(f"Erro ao converter CSV para Parquet: {e}")
            raise

    def convert_xlsx_to_parquet(
        self,
        xlsx_bytes: bytes,
        sheet_name: Optional[str] = None,
    ) -> tuple[bytes, dict]:
        """
        Converte XLSX para Parquet.
        Retorna (parquet_bytes, schema_info).
        """
        try:
            sheet = sheet_name or 0
            df = pd.read_excel(
                io.BytesIO(xlsx_bytes),
                sheet_name=sheet,
                nrows=self.MAX_ROWS,
            )
            return self._dataframe_to_parquet(df)
        except Exception as e:
            logger.error(f"Erro ao converter XLSX para Parquet: {e}")
            raise

    def _dataframe_to_parquet(self, df: pd.DataFrame) -> tuple[bytes, dict]:
        """Converte DataFrame para bytes Parquet + extrai schema."""
        # Sanitizar nomes de colunas
        df.columns = [self._sanitize_column_name(col) for col in df.columns]

        # Inferir tipos
        df = self._optimize_dtypes(df)

        # Converter para PyArrow
        table = pa.Table.from_pandas(df, preserve_index=False)

        # Serializar para bytes
        buffer = io.BytesIO()
        pq.write_table(
            table,
            buffer,
            compression=self.DEFAULT_COMPRESSION,
            version="2.6",
        )
        parquet_bytes = buffer.getvalue()

        # Extrair schema
        schema_info = self._extract_schema(df, table.schema)
        schema_info["row_count"] = len(df)
        schema_info["parquet_size_bytes"] = len(parquet_bytes)

        logger.info(
            f"Parquet gerado: {len(df)} linhas, "
            f"{len(df.columns)} colunas, "
            f"{len(parquet_bytes) / 1024:.1f} KB"
        )

        return parquet_bytes, schema_info

    def _extract_schema(self, df: pd.DataFrame, arrow_schema: pa.Schema) -> dict:
        """Extrai schema no formato Agent-BI."""
        columns = []
        for col in df.columns:
            dtype = str(df[col].dtype)
            arrow_type = str(arrow_schema.field(col).type) if col in arrow_schema.names else dtype

            glue_type = self._pandas_to_glue_type(dtype)
            columns.append({
                "name": col,
                "type": glue_type,
                "pandas_type": dtype,
                "arrow_type": arrow_type,
                "nullable": df[col].isna().any(),
                "null_count": int(df[col].isna().sum()),
                "sample_values": self._get_sample_values(df[col]),
                "description": f"{col}"
            })

        return {
            "columns": columns,
            "column_count": len(columns),
        }

    def _optimize_dtypes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Otimiza tipos de dados para reduzir tamanho."""
        for col in df.columns:
            if df[col].dtype == object:
                # 1. Tenta datetime robusto
                try:
                    # Salva uma cópia para comparar se a conversão foi útil
                    converted_dt = self._robust_to_datetime(df[col])
                    if not converted_dt.equals(df[col]) and "datetime" in str(converted_dt.dtype):
                        df[col] = converted_dt
                        continue
                except (ValueError, TypeError):
                    pass

                # 2. Tenta numérico
                try:
                    df[col] = pd.to_numeric(df[col])
                    continue
                except (ValueError, TypeError):
                    pass

        return df

    def _robust_to_datetime(self, series: pd.Series) -> pd.Series:
        """Tenta converter para datetime usando múltiplos formatos comuns."""
        if series.dtype != object:
            return series

        # 1. Tenta padrão do pandas com dayfirst=True (comum no Brasil)
        try:
            converted = pd.to_datetime(series, dayfirst=True, errors="coerce")
            if converted.notna().sum() > 0:
                return converted
        except Exception:
            pass

        # 2. Tenta formatos específicos se falhar ou retornar NaT
        formats = ["%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y"]
        for fmt in formats:
            try:
                converted = pd.to_datetime(series, format=fmt, errors="coerce")
                # Se converter uma parte significativa (>10% e maior que zero), aceita
                if converted.notna().sum() > 0:
                    return converted
            except Exception:
                continue

        return series

    @staticmethod
    def _sanitize_column_name(name: str) -> str:
        """Normaliza nome de coluna para compatibilidade com Athena/Glue."""
        import re
        name = str(name).strip()
        name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        name = re.sub(r"_+", "_", name)
        name = name.strip("_").lower()
        if not name or name[0].isdigit():
            name = f"col_{name}"
        return name[:255]

    @staticmethod
    def _pandas_to_glue_type(pandas_type: str) -> str:
        """Converte tipos pandas para tipos Glue/Athena."""
        mapping = {
            "int64": "bigint",
            "int32": "int",
            "int16": "smallint",
            "int8": "tinyint",
            "float64": "double",
            "float32": "float",
            "bool": "boolean",
            "object": "string",
            "datetime64[ns]": "timestamp",
            "datetime64[us]": "timestamp",
        }
        return mapping.get(pandas_type, "string")

    @staticmethod
    def _get_sample_values(series: pd.Series, n: int = 3) -> list:
        """Obtém amostras de valores não-nulos."""
        non_null = series.dropna().head(n)
        return [str(v) for v in non_null.tolist()]

    def infer_schema_from_bytes(
        self, file_bytes: bytes, file_extension: str
    ) -> dict:
        """Infere schema sem converter (apenas amostra)."""
        try:
            if file_extension.lower() == "csv":
                df = pd.read_csv(io.BytesIO(file_bytes), nrows=100)
            elif file_extension.lower() in ["xlsx", "xls"]:
                df = pd.read_excel(io.BytesIO(file_bytes), nrows=100)
            else:
                raise ValueError(f"Extensão não suportada: {file_extension}")

            _, schema_info = self._dataframe_to_parquet(df.head(10))
            return schema_info
        except Exception as e:
            logger.error(f"Erro ao inferir schema: {e}")
            raise

    def build_data_profile(self, df: pd.DataFrame) -> dict:
        """
        Gera um perfil estatístico compacto do DataFrame.

        Substitui o envio de centenas de linhas brutas para a LLM por um
        resumo inteligente por coluna (~10x menor em tokens):
          - Colunas categóricas: top 10 valores com frequência relativa (%)
          - Colunas numéricas: min, max, mean, stddev, p25/p50/p75
          - Colunas de data: data mínima e máxima
          - Todas: cardinalidade (nº únicos) e taxa de nulos (%)
        """
        profile: dict = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": {},
        }

        for col in df.columns:
            series = df[col]
            total = len(series)
            null_count = int(series.isna().sum())
            null_pct = round(null_count / total * 100, 1) if total else 0
            n_unique = int(series.nunique(dropna=True))

            col_info: dict = {
                "null_pct": null_pct,
                "unique_count": n_unique,
            }

            dtype = str(series.dtype)

            if dtype in ("int64", "int32", "int16", "int8", "float64", "float32"):
                numeric = series.dropna()
                if len(numeric) > 0:
                    try:
                        desc = numeric.describe(percentiles=[0.25, 0.5, 0.75])
                        col_info["type"] = "numeric"
                        col_info["min"] = self._safe_scalar(desc.get("min"))
                        col_info["max"] = self._safe_scalar(desc.get("max"))
                        col_info["mean"] = round(float(desc.get("mean", 0)), 2)
                        col_info["stddev"] = round(float(desc.get("std", 0)), 2)
                        col_info["p25"] = self._safe_scalar(desc.get("25%"))
                        col_info["p50"] = self._safe_scalar(desc.get("50%"))
                        col_info["p75"] = self._safe_scalar(desc.get("75%"))
                    except Exception:
                        col_info["type"] = "numeric"
            elif "datetime" in dtype:
                dated = series.dropna()
                if len(dated) > 0:
                    try:
                        col_info["type"] = "datetime"
                        col_info["min"] = str(dated.min())
                        col_info["max"] = str(dated.max())
                    except Exception:
                        col_info["type"] = "datetime"
            else:
                col_info["type"] = "categorical"
                try:
                    counts = series.dropna().astype(str).value_counts(normalize=False)
                    top_n = counts.head(10)
                    total_non_null = counts.sum() or 1
                    col_info["top_values"] = [
                        {
                            "value": str(val),
                            "count": int(cnt),
                            "pct": round(cnt / total_non_null * 100, 1),
                        }
                        for val, cnt in top_n.items()
                    ]
                    col_info["coverage_pct"] = round(
                        top_n.sum() / total_non_null * 100, 1
                    )
                except Exception:
                    col_info["top_values"] = []

            profile["columns"][col] = col_info

        logger.info(
            "DataProfile gerado: %d colunas, %d linhas analisadas",
            len(df.columns),
            len(df),
        )
        return profile

    def build_temporal_profile(self, df: pd.DataFrame) -> dict:
        """
        Gera um perfil de tendência temporal (Camada 2).
        Identifica colunas de data e resume métricas numéricas por mês.
        """
        temporal_profile = {"series": [], "has_temporal_data": False}
        
        # 1. Identificar colunas de data
        date_cols = [col for col in df.columns if "datetime" in str(df[col].dtype)]
        if not date_cols:
            # Tentar converter objetos que parecem datas
            for col in df.select_dtypes(include=["object"]).columns:
                try:
                    df[col] = pd.to_datetime(df[col])
                    date_cols.append(col)
                    break # Usar apenas a primeira para o perfil principal
                except Exception:
                    continue
        
        if not date_cols:
            return temporal_profile
            
        time_col = date_cols[0]
        temporal_profile["has_temporal_data"] = True
        temporal_profile["time_dimension"] = time_col
        
        # 2. Identificar colunas numéricas para agregar
        num_cols = [
            col for col in df.columns 
            if str(df[col].dtype) in ("int64", "float64") and col != time_col
        ][:5] # Limitar a 5 para manter o JSON leve
        
        if not num_cols:
            return temporal_profile

        try:
            # 3. Agregação Mensal
            df_temp = df.set_index(time_col)
            monthly = df_temp[num_cols].resample("ME").agg(["sum", "mean", "count"])
            
            # Formatar para JSON amigável
            history = []
            for date, row in monthly.iterrows():
                entry = {"date": date.strftime("%Y-%m-%d")}
                for col in num_cols:
                    entry[f"{col}_sum"] = self._safe_scalar(row[(col, "sum")])
                    entry[f"{col}_avg"] = self._safe_scalar(row[(col, "mean")])
                entry["volume"] = int(row[(num_cols[0], "count")])
                history.append(entry)
                
            temporal_profile["monthly_history"] = history[-24:] # Últimos 24 meses
            
        except Exception as e:
            logger.warning("[ParquetService] Falha ao gerar perfil temporal: %s", e)
            
        return temporal_profile

    @staticmethod
    def _safe_scalar(value):
        """Converte numpy scalar para tipo Python nativo."""
        try:
            v = float(value)
            return int(v) if v == int(v) else round(v, 4)
        except (TypeError, ValueError):
            return None
