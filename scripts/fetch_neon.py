"""
Simple Neon fetch script for testing connectivity and fetching sample rows.

Outputs JSON to `output/neon_fetch_result.json` and prints summary to stdout.
"""
import os
import json
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor

# Prefer env var, fallback to the dashboard constant if present
DB_CONNECTION_STRING = os.environ.get('NEON_DB_URL')
if not DB_CONNECTION_STRING:
    # Fallback to known connection string in dashboard_final.py
    DB_CONNECTION_STRING = "postgresql://neondb_owner:npg_RH4tS6KTciYv@ep-cool-bread-a4sb2gq8-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

OUT_PATH = Path(__file__).resolve().parents[1] / 'output' / 'neon_fetch_result.json'


def fetch():
    result = {'status': 'starting', 'errors': []}
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        result['status'] = 'connected'
    except Exception as e:
        result['status'] = 'connection_failed'
        result['errors'].append(str(e))
        print(json.dumps(result, indent=2))
        return

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # List tables in dq_validator schema
            try:
                cur.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'dq_validator'")
                tbls = [r['tablename'] for r in cur.fetchall()]
                result['dq_validator_tables'] = tbls
            except Exception as e:
                result['dq_validator_tables_error'] = str(e)

            # Check sample_policy_data (project's main data table)
            try:
                cur.execute('SELECT COUNT(*) AS cnt FROM dq_validator.sample_policy_data')
                raw_count = cur.fetchone()['cnt']
                result['sample_policy_data_count'] = raw_count
            except Exception as e:
                result['sample_policy_data_count_error'] = str(e)

            try:
                cur.execute('SELECT * FROM dq_validator.sample_policy_data LIMIT 5')
                rows = cur.fetchall()
                result['sample_policy_data_sample'] = rows
            except Exception as e:
                result['sample_policy_data_sample_error'] = str(e)

            # Check guidewire_policy_data_cleansing_rules (project's rules table)
            try:
                cur.execute('SELECT COUNT(*) AS cnt FROM dq_validator.guidewire_policy_data_cleansing_rules')
                rules_count = cur.fetchone()['cnt']
                result['guidewire_rules_count'] = rules_count
            except Exception as e:
                result['guidewire_rules_count_error'] = str(e)

            try:
                cur.execute('SELECT * FROM dq_validator.guidewire_policy_data_cleansing_rules LIMIT 50')
                rules = cur.fetchall()
                result['guidewire_rules_sample'] = rules
            except Exception as e:
                result['guidewire_rules_sample_error'] = str(e)

    except Exception as e:
        result['errors'].append(str(e))
    finally:
        try:
            conn.close()
        except Exception:
            pass

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, default=str)

    print(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    fetch()
