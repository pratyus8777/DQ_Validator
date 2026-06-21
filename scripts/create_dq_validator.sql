-- SQL DDL to create dq_validator schema and support tables
CREATE SCHEMA IF NOT EXISTS dq_validator;

-- Table to store cleansing rules
-- Guidewire-style policy cleansing rules table
CREATE TABLE IF NOT EXISTS dq_validator.guidewire_policy_data_cleansing_rules (
    s_no INTEGER,
    cde TEXT,
    completeness_remediation TEXT,
    validity_remediation TEXT,
    accuracy_remediation TEXT,
    consistency_remediation TEXT,
    deduplication_remediation TEXT,
    timeliness_remediation TEXT,
    integrity_remediation TEXT,
    reasonableness_remediation TEXT,
    column_name TEXT,
    rule_definition TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (column_name)
);

-- Table to store data quality profiles / metadata
CREATE TABLE IF NOT EXISTS dq_validator.data_profiles (
    profile_name TEXT PRIMARY KEY,
    profile JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Note: The raw_data table is created dynamically by the loader script
-- so we don't hardcode columns here. If you prefer a fixed DDL,
-- add a CREATE TABLE dq_validator.raw_data (...) statement matching your CSV headers.

-- Create a placeholder sample_policy_data table if not present. Loader will create full columns.
CREATE TABLE IF NOT EXISTS dq_validator.sample_policy_data (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sample seed for guidewire policy cleansing rules (idempotent)
INSERT INTO dq_validator.guidewire_policy_data_cleansing_rules (column_name, rule_definition)
VALUES
    ('Phone', 'Format as international E.164 where possible'),
    ('Email', 'Lowercase emails and strip whitespace')
ON CONFLICT (column_name) DO NOTHING;
