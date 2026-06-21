#!/usr/bin/env python
"""Check all available rule tables in dq_validator schema"""
import psycopg2
import os

conn = psycopg2.connect(
    os.environ.get('NEON_DB_URL') or 
    'postgresql://neondb_owner:npg_RH4tS6KTciYv@ep-cool-bread-a4sb2gq8-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require',
    connect_timeout=5
)
conn.set_session(autocommit=True)
cursor = conn.cursor()

print('='*70)
print('CHECKING ALL RULE TABLES IN dq_validator SCHEMA')
print('='*70)
print()

cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='dq_validator' ORDER BY table_name")
tables = cursor.fetchall()
print(f'Tables in dq_validator schema: {len(tables)} found')
print()

for table in tables:
    table_name = table[0]
    cursor.execute(f'SELECT COUNT(*) FROM dq_validator."{table_name}"')
    count = cursor.fetchone()[0]
    print(f'  ✓ {table_name}: {count} rows')

cursor.close()
conn.close()

print()
print('='*70)
print('All rule tables will be used for cleansing!')
print('='*70)
