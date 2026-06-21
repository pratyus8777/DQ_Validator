import pandas as pd
import psycopg2
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class NeonDBLearningStore:
    """
    Persists learning artifacts and results in NeonDB.
    Supports assessment results, corrections, and remediations.
    """

    def __init__(self, conn_str: str):
        self.conn_str = conn_str
        self.conn = None
        self._init_connection()
        self._ensure_tables()

    def _init_connection(self):
        """Initialize database connection."""
        try:
            self.conn = psycopg2.connect(self.conn_str)
            logger.info("Connected to NeonDB")
        except Exception as e:
            logger.error(f"Failed to connect to NeonDB: {e}")
            raise

    def _ensure_tables(self):
        """Ensure required tables exist."""
        try:
            cur = self.conn.cursor()
            
            # Correction memory table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS correction_memory (
                    id SERIAL PRIMARY KEY,
                    cde VARCHAR(255),
                    old_value TEXT,
                    new_value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Assessment results table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS dq_assessments (
                    id SERIAL PRIMARY KEY,
                    assessment_id VARCHAR(255) UNIQUE,
                    timestamp TIMESTAMP,
                    total_records INT,
                    issues_found INT,
                    pass_rate FLOAT,
                    before_or_after VARCHAR(50),
                    dimensions_json JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Remediation results table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS remediations (
                    id SERIAL PRIMARY KEY,
                    remediation_id VARCHAR(255) UNIQUE,
                    record_id VARCHAR(255),
                    column_name VARCHAR(255),
                    original_value TEXT,
                    new_value TEXT,
                    action VARCHAR(255),
                    confidence FLOAT,
                    approved BOOLEAN,
                    applied BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Clean data table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS policy_data_clean (
                    id SERIAL PRIMARY KEY,
                    data_json JSONB,
                    batch_id VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Dashboard KPIs table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS dq_kpis (
                    id SERIAL PRIMARY KEY,
                    kpi_name VARCHAR(255),
                    before_value FLOAT,
                    after_value FLOAT,
                    improvement_pct FLOAT,
                    batch_id VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self.conn.commit()
            logger.info("Database tables initialized")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            self.conn.rollback()
            raise

    def apply_corrections(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply stored corrections to dataframe."""
        try:
            query = "SELECT cde, old_value, new_value FROM correction_memory ORDER BY created_at DESC LIMIT 1000"
            corrections = pd.read_sql(query, self.conn)

            df = df.copy()
            for _, r in corrections.iterrows():
                df.loc[df[r["cde"]] == r["old_value"], r["cde"]] = r["new_value"]
            
            logger.info(f"Applied {len(corrections)} stored corrections")
            return df
        except Exception as e:
            logger.error(f"Failed to apply corrections: {e}")
            return df

    def persist_feedback(self, feedback: List[Dict[str, Any]]):
        """Persist user feedback as corrections."""
        try:
            cur = self.conn.cursor()
            for item in feedback:
                cur.execute(
                    """
                    INSERT INTO correction_memory (cde, old_value, new_value)
                    VALUES (%s, %s, %s)
                    """,
                    (item.get("cde"), item.get("old"), item.get("new"))
                )
            self.conn.commit()
            logger.info(f"Persisted {len(feedback)} feedback items")
        except Exception as e:
            logger.error(f"Failed to persist feedback: {e}")
            self.conn.rollback()
            raise

    def persist_assessment(self, assessment_id: str, assessment_data: Dict[str, Any]):
        """Persist DQ assessment results."""
        try:
            cur = self.conn.cursor()
            
            cur.execute(
                """
                INSERT INTO dq_assessments 
                (assessment_id, timestamp, total_records, issues_found, pass_rate, 
                 before_or_after, dimensions_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    assessment_id,
                    datetime.now(),
                    assessment_data.get("total_records"),
                    assessment_data.get("issues_found"),
                    assessment_data.get("pass_rate"),
                    assessment_data.get("before_or_after"),
                    json.dumps(assessment_data.get("dimensions", {}))
                )
            )
            
            self.conn.commit()
            logger.info(f"Persisted assessment {assessment_id}")
        except Exception as e:
            logger.error(f"Failed to persist assessment: {e}")
            self.conn.rollback()
            raise

    def persist_remediations(self, batch_id: str, remediations: List[Dict[str, Any]]):
        """Persist remediation records."""
        try:
            cur = self.conn.cursor()
            
            for rem in remediations:
                cur.execute(
                    """
                    INSERT INTO remediations 
                    (remediation_id, record_id, column_name, original_value, new_value, 
                     action, confidence, approved, applied)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        f"{batch_id}_{rem.get('record_id')}_{rem.get('column')}",
                        rem.get("record_id"),
                        rem.get("column"),
                        rem.get("original_value"),
                        rem.get("new_value"),
                        rem.get("action"),
                        rem.get("confidence", 0),
                        rem.get("approved", False),
                        rem.get("applied", False)
                    )
                )
            
            self.conn.commit()
            logger.info(f"Persisted {len(remediations)} remediations")
        except Exception as e:
            logger.error(f"Failed to persist remediations: {e}")
            self.conn.rollback()
            raise

    def persist_clean_data(self, batch_id: str, df: pd.DataFrame):
        """Persist cleaned dataset."""
        try:
            cur = self.conn.cursor()
            
            # Store as JSONB for flexible schema
            for idx, row in df.iterrows():
                row_dict = row.to_dict()
                cur.execute(
                    """
                    INSERT INTO policy_data_clean (data_json, batch_id)
                    VALUES (%s, %s)
                    """,
                    (json.dumps(row_dict, default=str), batch_id)
                )
            
            self.conn.commit()
            logger.info(f"Persisted {len(df)} clean records for batch {batch_id}")
        except Exception as e:
            logger.error(f"Failed to persist clean data: {e}")
            self.conn.rollback()
            raise

    def persist_kpis(self, batch_id: str, kpis: Dict[str, Dict[str, float]]):
        """Persist DQ improvement KPIs."""
        try:
            cur = self.conn.cursor()
            
            for kpi_name, values in kpis.items():
                before = values.get("before", 0)
                after = values.get("after", 0)
                improvement = ((after - before) / before * 100) if before > 0 else 0
                
                cur.execute(
                    """
                    INSERT INTO dq_kpis (kpi_name, before_value, after_value, improvement_pct, batch_id)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (kpi_name, before, after, improvement, batch_id)
                )
            
            self.conn.commit()
            logger.info(f"Persisted {len(kpis)} KPIs")
        except Exception as e:
            logger.error(f"Failed to persist KPIs: {e}")
            self.conn.rollback()
            raise

    def fetch_recent_assessments(self, limit: int = 10) -> pd.DataFrame:
        """Fetch recent assessment results."""
        try:
            query = """
                SELECT * FROM dq_assessments 
                ORDER BY created_at DESC 
                LIMIT %s
            """
            return pd.read_sql(query, self.conn, params=(limit,))
        except Exception as e:
            logger.error(f"Failed to fetch assessments: {e}")
            return pd.DataFrame()

    def fetch_recent_remediations(self, batch_id: Optional[str] = None, limit: int = 1000) -> pd.DataFrame:
        """Fetch recent remediation records."""
        try:
            if batch_id:
                query = """
                    SELECT * FROM remediations 
                    WHERE remediation_id LIKE %s
                    ORDER BY created_at DESC 
                    LIMIT %s
                """
                return pd.read_sql(query, self.conn, params=(f"{batch_id}%", limit))
            else:
                query = """
                    SELECT * FROM remediations 
                    ORDER BY created_at DESC 
                    LIMIT %s
                """
                return pd.read_sql(query, self.conn, params=(limit,))
        except Exception as e:
            logger.error(f"Failed to fetch remediations: {e}")
            return pd.DataFrame()

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
