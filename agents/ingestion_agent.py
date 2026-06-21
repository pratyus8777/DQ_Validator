import pandas as pd
import hashlib


class IngestionAgent:
    """
    Ingests and normalizes all inputs.
    Supports BOTH:
    - Long-form rule repositories
    - Wide-form (dimension-per-column) rule matrices
    """

    def __init__(self, data_source, llm_client=None):
        self.data_source = data_source
        self.llm = llm_client

    def ingest(self) -> dict:
        raw_df = self._normalize_columns(
            self.data_source.read_sample_data()
        )

        rules_raw = self._normalize_columns(
            self.data_source.read_rules()
        )

        cleansing_df = self._normalize_columns(
            self.data_source.read_cleansing_rules()
        )

        kpi_df = self._normalize_columns(
            self.data_source.read_kpis()
        )

        rules_df = self._normalize_rule_repository(rules_raw)

        schema_context = self._infer_schema(raw_df)

        return {
            "data": raw_df,
            "dq_rules": rules_df,
            "cleansing_rules": cleansing_df,
            "kpis": kpi_df,
            "schema_context": schema_context,
        }

    # ------------------------------------------------------------------
    # RULE REPOSITORY NORMALIZATION (THE KEY FIX)
    # ------------------------------------------------------------------
    def _normalize_rule_repository(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Converts wide or long rule repositories into canonical long format.
        """

        # LONG format already
        if {"rule_id", "dimension", "check_type", "cde"}.issubset(df.columns):
            return df

        # WIDE format detected
        if "cde" not in df.columns:
            raise ValueError(
                "Rule repository must contain 'cde' column. "
                f"Found columns: {list(df.columns)}"
            )

        dimension_columns = [
            c for c in df.columns
            if c not in {"s_no", "cde"}
        ]

        records = []

        for _, row in df.iterrows():
            cde = row["cde"]

            for dim_col in dimension_columns:
                value = row[dim_col]

                if pd.isna(value) or str(value).strip() == "":
                    continue

                dimension = self._clean_dimension_name(dim_col)
                check_type, parameters = self._parse_rule_cell(value)

                rule_id = self._generate_rule_id(
                    cde, dimension, check_type
                )

                records.append({
                    "rule_id": rule_id,
                    "cde": cde,
                    "dimension": dimension,
                    "check_type": check_type,
                    "parameters": parameters,
                })

        if not records:
            raise ValueError("No usable rules found after normalization.")

        return pd.DataFrame(records)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _clean_dimension_name(name: str) -> str:
        return (
            name.replace("_/_", "_")
                .replace("__", "_")
                .strip()
                .title()
        )

    @staticmethod
    def _parse_rule_cell(value):
        """
        Parses rule cell content.
        Examples:
        - 'not_null'
        - 'range:0,100'
        - 'regex:^[A-Z]{3}$'
        """
        text = str(value).strip()

        if ":" in text:
            check, params = text.split(":", 1)
            return check.strip(), params.strip()

        return text, None

    @staticmethod
    def _generate_rule_id(cde, dimension, check_type):
        raw = f"{cde}|{dimension}|{check_type}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    # ------------------------------------------------------------------
    # LLM-assisted schema understanding (optional)
    # ------------------------------------------------------------------
    def _infer_schema(self, df: pd.DataFrame) -> dict:
        if not self.llm:
            return {}

        prompt = f"""
        Infer business meaning of columns:
        {list(df.columns)}
        """

        response = self.llm.complete(prompt)
        return {"llm_schema_hint": response} if response else {}

    # ------------------------------------------------------------------
    # Column normalization
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = (
            df.columns.astype(str)
              .str.strip()
              .str.lower()
              .str.replace(" ", "_")
              .str.replace("-", "_")
        )
        return df
