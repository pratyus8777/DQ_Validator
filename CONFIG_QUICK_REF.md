# Configuration Quick Reference

## Three Config Modes

### 🔵 HYBRID (Default: `config/hybrid.yaml`)
**DB First, Local Fallback**
```
Settings → Neon DB ✓ → Local Files ✓ → Success
       ↓ (error)    ↓ (enabled)
```
- Best for: **Development + Testing**
- Priority: Try DB, fallback if unavailable

### 🟢 LOCAL (`config/local.yaml`)
**Local Files Only**
```
Settings → Skip DB → Local Files ✓ → Success
```
- Best for: **Offline Development**
- No DB access, pure CSV/JSON

### 🔴 CLOUD (`config/cloud.yaml`)
**DB Only, No Fallback**
```
Settings → Neon DB ✓ → Success
       ↓ (error)
      Fail
```
- Best for: **Production**
- Strict DB, no stale local files

---

## How to Use

### Switch Mode
```bash
# Use hybrid (default)
streamlit run dashboard_final.py

# Use local (offline)
set DQ_CONFIG=local.yaml && streamlit run dashboard_final.py

# Use cloud (strict)
set DQ_CONFIG=cloud.yaml && streamlit run dashboard_final.py
```

### In Code
```python
from data_io.db_helpers import read_sample_policy_data, read_guidewire_cleansing_rules
from data_io.config_loader import get_config

# Auto-uses config (hybrid by default)
df_data = read_sample_policy_data()
df_rules = read_guidewire_cleansing_rules()

# Check config status
cfg = get_config()
print(f"Mode: {cfg.get_mode()}")
print(f"DB enabled: {cfg.is_db_enabled()}")
print(f"Fallback: {cfg.should_fallback()}")
```

---

## Config Files Location
```
config/
  ├── hybrid.yaml  ← Default (DB + Fallback)
  ├── local.yaml   ← No DB, local files only
  ├── cloud.yaml   ← Strict DB only
  └── agentic.yaml ← For agentic mode
```

---

## Environment Variables
```bash
set DQ_CONFIG=cloud.yaml          # Switch config
set NEON_DB_URL=postgresql://...  # Override connection string
```

---

## Database Tables (dq_validator schema)
| Table | Config Key | Fallback File |
|-------|------------|---------------|
| `sample_policy_data` | `database.neon.sample_data_table` | `data/Sample_Policy_Data.csv` |
| `guidewire_policy_data_cleansing_rules` | `database.neon.rules_table` | `data/Guidewire_Policy_DataCleansing_Rules.csv` |

---

## Flow Diagram

```
Application
    ↓
read_sample_policy_data()
    ↓
db_helpers._read_from_db()
    ├─ Load config/hybrid.yaml
    ├─ Check: db.neon.enabled?
    │   ├─ YES → Connect to Neon DB
    │   │       └─ Success? → Return DF ✓
    │   │       └─ Error → Check fallback_on_error
    │   └─ NO → Skip to fallback
    ├─ Check: fallback_on_error?
    │   ├─ YES → Read CSV file
    │   │       └─ Return DF ✓
    │   └─ NO → Return empty DF
    └─ Logging
```

---

## Key Methods

### Get Config Values
```python
cfg = get_config()

cfg.get('mode')                           # 'hybrid'
cfg.get('database.neon.enabled')          # True
cfg.get('database.neon.schema')           # 'dq_validator'
cfg.get_db_tables()                       # {'sample_data': '...', 'rules': '...'}
cfg.get_local_paths()                     # {'sample_data': '...', ...}
```

### Helper Methods
```python
cfg.is_db_enabled()      # True/False
cfg.should_fallback()    # True/False
cfg.get_mode()           # 'hybrid'/'local'/'cloud'
cfg.get_db_schema()      # 'dq_validator'
cfg.get_output_dir()     # 'output/'
```

---

## Data Sources Priority

| Mode | Priority 1 | Priority 2 | Priority 3 |
|------|-----------|-----------|-----------|
| Hybrid | Neon DB | CSV file | Empty DF |
| Local | CSV file | Empty DF | - |
| Cloud | Neon DB | Error | - |

---

## Testing

```bash
# Test config loading
python -c "from data_io.config_loader import get_config; cfg = get_config(); print(cfg)"

# Test db_helpers with hybrid
python -c "from data_io.db_helpers import read_sample_policy_data; print(len(read_sample_policy_data()))"

# Test with local config
set DQ_CONFIG=local.yaml
python -c "from data_io.db_helpers import read_guidewire_cleansing_rules; print(len(read_guidewire_cleansing_rules()))"
```

