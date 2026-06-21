"""Database helpers for Neon PostgreSQL with hybrid fallback support."""
import os
from pathlib import Path
import pandas as pd
import psycopg2
import logging
from data_io.config_loader import get_config

logger = logging.getLogger(__name__)

DB_CONNECTION_STRING = os.environ.get('NEON_DB_URL') or "postgresql://neondb_owner:npg_RH4tS6KTciYv@ep-cool-bread-a4sb2gq8-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"


def get_config_manager():
    """Get config manager instance."""
    return get_config()


def get_connection():
    """Get Neon DB connection."""
    conn = psycopg2.connect(DB_CONNECTION_STRING, connect_timeout=5)
    conn.set_session(autocommit=True)
    return conn


def _read_from_db(query: str, fallback_file: str = None) -> pd.DataFrame:
    """Execute query on DB; fall back to local file if needed."""
    cfg = get_config_manager()
    
    if cfg.is_db_enabled():
        try:
            conn = None
            try:
                conn = get_connection()
                df = pd.read_sql(query, conn)
                return df
            finally:
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
        except Exception as e:
            logger.warning(f"DB read failed: {e}")
            if not cfg.should_fallback():
                raise
    
    if fallback_file and cfg.should_fallback():
        path = Path(fallback_file)
        if path.exists():
            logger.info(f"Using fallback file: {fallback_file}")
            if fallback_file.endswith('.csv'):
                return pd.read_csv(fallback_file)
            elif fallback_file.endswith('.json'):
                return pd.read_json(fallback_file)
    
    return pd.DataFrame()


def read_sample_policy_data(limit: int = 1000) -> pd.DataFrame:
    """Read sample policy data from DB or fallback CSV."""
    cfg = get_config_manager()
    schema = cfg.get_db_schema()
    table = cfg.get_db_tables()['sample_data']
    query = f"SELECT * FROM {schema}.{table} LIMIT {int(limit)}"
    fallback = cfg.get_local_paths().get('sample_data')
    return _read_from_db(query, fallback)


def read_guidewire_cleansing_rules() -> pd.DataFrame:
    """Read cleansing rules from DB or fallback CSV."""
    cfg = get_config_manager()
    schema = cfg.get_db_schema()
    table = cfg.get_db_tables()['rules']
    query = f"SELECT * FROM {schema}.{table}"
    fallback = cfg.get_local_paths().get('cleansing_rules')
    return _read_from_db(query, fallback)
