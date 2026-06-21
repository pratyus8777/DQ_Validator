# Configuration Guide - Hybrid DQ System

## Overview
The DQ system now uses **YAML-based configuration** to manage multiple deployment modes and seamlessly switch between Neon DB (primary) and local files (fallback).

---

## Architecture

### ConfigManager (Singleton)
- **Location**: `data_io/config_loader.py`
- **Purpose**: Centralized configuration management
- **Loading Priority**:
  1. Explicit config file via `DQ_CONFIG` env var
  2. Default: `config/hybrid.yaml`

### Database Helpers
- **Location**: `data_io/db_helpers.py`
- **Purpose**: Abstracted DB/file reads using config
- **Functions**:
  - `read_sample_policy_data()` → queries `dq_validator.sample_policy_data` or falls back to CSV
  - `read_guidewire_cleansing_rules()` → queries `dq_validator.guidewire_policy_data_cleansing_rules` or falls back to CSV

---

## Configuration Modes

### 1. **HYBRID Mode** (Default) `config/hybrid.yaml`
```yaml
database:
  primary: neon
  neon:
    enabled: true
  fallback_on_error: true  # If DB unavailable, use local files
```
- **Use Case**: Development + Production
- **Behavior**:
  - Attempts to read from Neon DB (`dq_validator` schema)
  - Falls back to local CSV/JSON if DB unavailable
  - Graceful degradation without manual intervention

---

### 2. **LOCAL Mode** `config/local.yaml`
```yaml
database:
  neon:
    enabled: false  # No DB access
```
- **Use Case**: Local development without Neon connection
- **Behavior**:
  - Reads ONLY from local files (CSV/JSON)
  - No DB connections attempted
  - Fastest for offline work

---

### 3. **CLOUD Mode** `config/cloud.yaml`
```yaml
database:
  neon:
    enabled: true
  fallback_on_error: false  # Strict DB-only
```
- **Use Case**: Production environment
- **Behavior**:
  - Reads ONLY from Neon DB
  - Fails fast if DB unavailable
  - No fallback to potentially stale local files

---

## Usage

### Switch Configuration

**Option A: Environment Variable**
```bash
set DQ_CONFIG=local.yaml
python dashboard_final.py
```

**Option B: Programmatic**
```python
from data_io.config_loader import get_config

cfg = get_config()
print(cfg.get_mode())          # hybrid
print(cfg.is_db_enabled())     # True
print(cfg.should_fallback())   # True
```

### Example Usage in Code

**Before (Hardcoded)**
```python
df = pd.read_sql("SELECT * FROM dq_validator.sample_policy_data", conn)
```

**After (Config-Driven)**
```python
from data_io.db_helpers import read_sample_policy_data

df = read_sample_policy_data()  # Uses config to determine source
```

---

## Configuration Structure

### Database Section
```yaml
database:
  primary: neon              # Primary data source: neon | local
  neon:
    enabled: true            # Enable Neon DB reads
    schema: dq_validator     # Neon schema name
    sample_data_table: sample_policy_data
    rules_table: guidewire_policy_data_cleansing_rules
  fallback_on_error: true    # Fall back to local files if DB fails
```

### Paths Section
```yaml
paths:
  sample_data: data/Sample_Policy_Data.csv
  cleansing_rules: data/Guidewire_Policy_DataCleansing_Rules.csv
```

### Output Section
```yaml
output:
  dir: output/
  cleansing_rules_json: output/cleansing_rules.json
```

---

## Access Configuration Values

### In Python
```python
from data_io.config_loader import get_config

cfg = get_config()

# Simple values
mode = cfg.get('mode')  # 'hybrid'

# Nested values (dot notation)
schema = cfg.get('database.neon.schema')  # 'dq_validator'
tables = cfg.get('database.neon.rules_table')  # 'guidewire_policy_data_cleansing_rules'

# Helper methods
cfg.is_db_enabled()
cfg.should_fallback()
cfg.get_mode()
cfg.get_db_schema()
cfg.get_db_tables()
cfg.get_local_paths()
```

---

## Data Flow Example

### Hybrid Mode (with fallback)
```
read_sample_policy_data()
  ├─ Check: is_db_enabled() → True
  ├─ Try: Query dq_validator.sample_policy_data
  ├─ Success? → Return DF
  └─ Failure:
      ├─ Check: should_fallback() → True
      ├─ Try: Read data/Sample_Policy_Data.csv
      └─ Return DF (or empty if file missing)
```

### Cloud Mode (strict DB)
```
read_sample_policy_data()
  ├─ Check: is_db_enabled() → True
  ├─ Try: Query dq_validator.sample_policy_data
  ├─ Success? → Return DF
  └─ Failure: Raise error (no fallback)
```

### Local Mode (no DB)
```
read_sample_policy_data()
  ├─ Check: is_db_enabled() → False
  ├─ Try: Read data/Sample_Policy_Data.csv
  └─ Return DF
```

---

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `DQ_CONFIG` | Config file to load | `hybrid.yaml` |
| `NEON_DB_URL` | Neon connection string | Embedded in code |

---

## Best Practices

1. **Development**: Use `local.yaml` (no external dependencies)
2. **Testing**: Use `hybrid.yaml` (tests both paths)
3. **Production**: Use `cloud.yaml` (strict DB, no fallback)
4. **CI/CD**: Set `DQ_CONFIG` env var explicitly

---

## Migration Checklist

- [x] Create `ConfigManager` class
- [x] Update `db_helpers.py` to use config
- [x] Update `dashboard_final.py` to load config
- [x] Create `config/hybrid.yaml` with DB settings
- [x] Update `config/local.yaml` with fallback settings
- [x] Update `config/cloud.yaml` for strict DB mode
- [ ] Update remaining modules to use `read_sample_policy_data()` and `read_guidewire_cleansing_rules()` instead of hardcoded paths
- [ ] Test all 3 modes (hybrid, local, cloud)

---

## Troubleshooting

### "Config file not found"
```python
# Ensure config/ directory exists and contains YAML files
ls config/
# Output: agentic.yaml  cloud.yaml  hybrid.yaml  local.yaml
```

### "DB connection failed, no fallback"
```python
cfg = get_config()
print(cfg.should_fallback())  # Check if fallback enabled
# In cloud.yaml, fallback_on_error: false is intentional
```

### "Using wrong config file"
```bash
# Check which file was loaded
set DQ_CONFIG=  # Clear env var
# Now default hybrid.yaml will load
```

---

## See Also
- [Dashboard Guide](../dashboard_final.py) - Uses ConfigManager
- [DB Helpers](../data_io/db_helpers.py) - Config-driven reads
- [Assessment Pipeline](../assessment_first_pipeline.py) - Config integration

