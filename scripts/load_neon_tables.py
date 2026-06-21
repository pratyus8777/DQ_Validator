"""
Loader script to create dq_validator.sample_policy_data table based on CSV header
and bulk-insert rows into Neon Postgres.

Usage:
  - Install dependencies: pip install psycopg2-binary pandas
  - Ensure the CSV exists at `data/Sample_Policy_Data.csv` (relative to repo root)
  - Set environment variable `NEON_DB_URL` to your connection string, or edit DB_CONNECTION_STRING below
  - Run: python scripts/load_neon_tables.py

The script will:
  1. Create schema `dq_validator` and support tables (if missing) using the SQL file
  2. Create `dq_validator.sample_policy_data` with columns that match the CSV headers (as TEXT)
  3. Bulk-insert CSV rows
  4. Optionally seed `cleansing_rules` from output/cleansing_rules.json if present
"""

import os
import csv
import json
from pathlib import Path
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values

# Fill this or set NEON_DB_URL env var. Using env var is recommended.
DB_CONNECTION_STRING = os.environ.get('NEON_DB_URL', "postgresql://neondb_owner:npg_RH4tS6KTciYv@ep-cool-bread-a4sb2gq8-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")

REPO_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = REPO_ROOT / 'data' / 'Sample_Policy_Data.csv'
DDL_FILE = REPO_ROOT / 'scripts' / 'create_dq_validator.sql'
RULES_JSON = REPO_ROOT / 'output' / 'cleansing_rules.json'


def ensure_connection():
    if not DB_CONNECTION_STRING:
        raise RuntimeError('Set NEON_DB_URL environment variable or edit DB_CONNECTION_STRING in this script')
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    return conn


def run_sql_file(conn, sql_path):
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql_text = f.read()
    with conn.cursor() as cur:
        cur.execute(sql_text)
    conn.commit()


def create_raw_table_from_csv(conn, csv_path):
    # Read header
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        headers = next(reader)

    # Build CREATE TABLE statement with TEXT columns (safe default)
    quoted_cols = [sql.Identifier(h) for h in headers]
    col_defs = sql.SQL(', ').join(sql.SQL('{} TEXT').format(c) for c in quoted_cols)

    # Create sample_policy_data with CSV-derived columns
    create_stmt = sql.SQL('CREATE TABLE IF NOT EXISTS dq_validator.sample_policy_data (id SERIAL PRIMARY KEY, {cols}, created_at TIMESTAMPTZ DEFAULT NOW())').format(cols=col_defs)

    with conn.cursor() as cur:
        cur.execute(create_stmt)
    conn.commit()
    print(f'Created/ensured dq_validator.sample_policy_data with columns: {headers}')

    # Insert data using execute_values for speed
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            # ensure column order matches headers
            rows.append(tuple(r.get(h, None) for h in headers))

    if not rows:
        print('No rows found in CSV — nothing to insert.')
        return

    cols_sql = sql.SQL(', ').join(quoted_cols)
    insert_sql = sql.SQL('INSERT INTO dq_validator.sample_policy_data ({cols}) VALUES %s').format(cols=cols_sql)

    with conn.cursor() as cur:
        execute_values(cur, insert_sql.as_string(conn), rows, template=None, page_size=1000)
    conn.commit()
    print(f'Inserted {len(rows)} rows into dq_validator.sample_policy_data')


def seed_rules_from_json(conn, json_path):
    if not json_path.exists():
        print('No rules JSON found to seed.')
        return
    with open(json_path, 'r', encoding='utf-8') as f:
        rules = json.load(f)

    with conn.cursor() as cur:
        for col, rule in rules.items():
            cur.execute(
                """
                INSERT INTO dq_validator.guidewire_policy_data_cleansing_rules (column_name, rule_definition, created_at, updated_at)
                VALUES (%s, %s, NOW(), NOW())
                ON CONFLICT (column_name) DO UPDATE SET rule_definition = EXCLUDED.rule_definition, updated_at = NOW()
                """,
                (col, str(rule))
            )
    conn.commit()
    print(f'Seeded {len(rules)} rules into dq_validator.cleansing_rules')


def main():
    if not CSV_PATH.exists():
        print(f'CSV not found at {CSV_PATH}. Please place your Sample_Policy_Data.csv there and retry.')
        return

    conn = ensure_connection()

    # Create schema and support tables from DDL
    if DDL_FILE.exists():
        run_sql_file(conn, DDL_FILE)
        print('Executed DDL to create schema and support tables.')
    else:
        print(f'Could not find DDL file at {DDL_FILE}. Proceeding to create raw table and support tables programmatically.')
        with conn.cursor() as cur:
            cur.execute('CREATE SCHEMA IF NOT EXISTS dq_validator')
            cur.execute('''CREATE TABLE IF NOT EXISTS dq_validator.cleansing_rules (column_name TEXT PRIMARY KEY, rule_definition TEXT, created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW())''')
            cur.execute('''CREATE TABLE IF NOT EXISTS dq_validator.data_profiles (profile_name TEXT PRIMARY KEY, profile JSONB, created_at TIMESTAMPTZ DEFAULT NOW())''')
        conn.commit()

    # Create raw table and load CSV
    create_raw_table_from_csv(conn, CSV_PATH)

    # Seed rules if json exists
    seed_rules_from_json(conn, RULES_JSON)

    conn.close()
    print('Done. Dashboard should now be able to read from dq_validator.* tables.')


if __name__ == '__main__':
    main()
