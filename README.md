# Data Quality & Remediation (DQ_PE) Platform

A comprehensive AI-powered data quality assessment and remediation system for insurance policy data. This platform evaluates data across 6 dimensions, identifies quality issues, applies intelligent remediation, and learns from human feedback.

## Overview

The DQ_PE platform provides:
- **Multi-dimensional data quality assessment** (Accuracy, Completeness, Consistency, Timeliness, Uniqueness, Relevance)
- **Automated remediation** of quality issues using LLM-powered agents
- **Human-in-the-loop (HITL)** feedback integration
- **Learning engine** that improves over time
- **Flexible architecture** supporting local, hybrid, and cloud deployments

### 🚀 NEW: Enhanced LLM Integration for Intelligent User Input Processing

The platform now features **intelligent LLM interpretation** of user-provided cleansing rules:
- 📝 **Context-Aware Rule Interpretation**: LLM reads user inputs with full data context (sample values)
- 🎯 **Structured Rule Processing**: Standardized TRANSFORMATION | PARAMETERS | LOGIC format
- ⚡ **Parallel Processing**: 5-worker ThreadPool for fast transformation determination
- 🔄 **Fallback Heuristics**: Graceful degradation when LLM unavailable
- 📊 **Transparent Logging**: All LLM decisions logged for audit trail

**Quick Links**:
- 📖 [LLM Enhancement Guide](LLM_ENHANCED_INTEGRATION.md) - Detailed technical documentation
- 🎓 [LLM Quick Start](LLM_QUICK_START.md) - Simple step-by-step guide
- 📚 [Real Examples](LLM_EXAMPLES.md) - 7 detailed real-world examples

**Example**: User says "standardize phone numbers" → LLM intelligently converts "5551234567" → "(555) 123-4567"

## Architecture

### Core Components

1. **Agents** (`agents/`) - Modular agents for specific tasks:
   - Quality assessment agents (Accuracy, Completeness, etc.)
   - Remediation and improvement agents
   - Human feedback and learning agents
   - Reporting and orchestration agents

2. **Data I/O** (`data_io/`) - Data source abstraction:
   - Local file system support
   - S3/cloud storage support
   - Learning store persistence (local JSON or NeonDB)

3. **Rules Engine** (`rules_engine/`) - DQ rule execution:
   - Check functions for violations
   - Fix action functions for remediation
   - Extensible registry pattern

4. **LLM Client** (`llm/`) - LLM provider wrapper:
   - Provider-agnostic interface
   - Timeout and error handling
   - Extensible for OpenAI, Claude, etc.

5. **Dashboard** (`dashboard/`) - Pre/post HITL visualizations

## Quick Start

### Prerequisites
- Python 3.9+
- pandas, pyyaml, psycopg2 (see requirements.txt)

### Installation

```bash
pip install -r requirements.txt
```

### Configuration

Edit `config/local.yaml` or create a new configuration file:

```yaml
mode: local

paths:
  sample_data: data/Sample_Policy_Data.csv
  dq_rules: data/DQ_Rule_Repository-Policy.csv
  cleansing_rules: data/Guidewire_Policy_DataCleansing_Rules.csv
  kpis: data/DQ_Dashboard_KPIs.csv

thresholds:
  remediation_trigger_pct: 0.05  # Trigger remediation if >5% issues found

llm:
  enabled: true
  model: gpt-4.1-mini
  timeout: 5

output_dir: output/

learning:
  type: local
  path: output/learning_memory.json
```

### Running the Pipeline

```bash
python cli.py config/local.yaml
```

## Output Files

The pipeline generates:
- `DQ_Assessment_result.csv` - Quality violations by dimension
- `DQ_Improvement_KPIs.csv` - Before/after issue counts
- `Sample_Policy_Data_clean.csv` - Remediated dataset
- `run_metadata.json` - Execution metadata (timestamp, record counts)

## Deployment Modes

### Local Mode
All data sourced from local filesystem, outputs written locally.

```yaml
mode: local
paths:
  sample_data: data/Sample_Policy_Data.csv
  ...
```

### Hybrid Mode
Inputs from cloud (S3), outputs to local filesystem.

```yaml
mode: hybrid
s3:
  bucket: dq-artifacts
  prefix: dq-inputs/
```

### Cloud Mode
Full cloud deployment with S3 inputs/outputs and NeonDB learning store.

```yaml
mode: cloud
s3:
  bucket: dq-artifacts
  prefix: dq-inputs/
learning:
  type: neondb
  connection_string: postgresql://...
```

## Data Quality Dimensions

1. **Accuracy** - Does the data match trusted sources?
2. **Completeness** - Are required fields populated?
3. **Consistency** - Is data uniform across systems?
4. **Timeliness** - Is data current and up-to-date?
5. **Uniqueness** - Are there unwanted duplicates?
6. **Relevance** - Is data valid for its business purpose?

## Pipeline Flow

```
1. INGEST
   ├─ Load sample data & metadata
   └─ Initialize context

2. PROFILE (BEFORE)
   ├─ Run 6 quality assessment agents
   ├─ Aggregate violations
   └─ Store baseline metrics

3. GATE (Threshold Check)
   ├─ Evaluate violation rate vs threshold
   └─ Decide remediation approval

4. REMEDIATION
   ├─ Apply fix actions to violations
   ├─ LLM-powered for complex issues
   └─ Generate remediated dataset

5. PROFILE (AFTER)
   ├─ Re-assess remediated data
   └─ Measure improvement

6. FEEDBACK / LEARNING
   ├─ Collect human corrections
   ├─ Apply prior learnings
   └─ Store new corrections for future runs

7. FINAL CLEAN
   └─ Standardize output format

8. REPORTING
   ├─ Generate KPIs
   └─ Write outputs
```

## Extending the Platform

### Adding a New Quality Agent

1. Create `agents/custom_agent.py`:

```python
from agents.base_quality_agent import BaseQualityAgent

class CustomAgent(BaseQualityAgent):
    def run(self, context: dict) -> dict:
        violations = [...]
        return {
            "dimension": "custom",
            "violations": violations
        }
```

2. Register in `cli.py`:

```python
from agents.custom_agent import CustomAgent

quality_agents = [
    ...,
    CustomAgent(llm_client),
]
```

### Adding a New Fix Action

1. Define function in `rules_engine/fix_actions.py`:

```python
def custom_fix(df, rule, llm_client=None):
    # Apply remediation logic
    return df
```

2. Register in `FIX_ACTION_REGISTRY`:

```python
FIX_ACTION_REGISTRY = {
    ...,
    "custom_fix": custom_fix,
}
```

## Configuration Management

All configuration is YAML-based for portability. Key sections:

- `mode` - Deployment mode (local/hybrid/cloud)
- `paths` - Data file locations
- `thresholds` - Quality gates and remediation triggers
- `llm` - LLM provider settings
- `learning` - Learning store configuration
- `output_dir` - Output directory

## Error Handling & Logging

The platform includes:
- Comprehensive logging at INFO and DEBUG levels
- Exception handling with graceful degradation
- Validation of configurations and data at each stage
- Detailed error reporting in logs

## Performance

- Handles 200+ row datasets efficiently in memory
- Batch processing for large remediation operations
- Optional LLM caching to reduce API calls
- Learning store lookups optimized via indexed access

## Testing

Run unit tests:

```bash
pytest tests/ -v
```

## Contributing

1. Follow PEP 8 style guidelines
2. Add type hints to all functions
3. Include docstrings for public APIs
4. Write tests for new features
5. Update README for new capabilities

## License

[Add your license here]

## Support

For issues or questions:
- Check configuration files for common errors
- Review logs in `output/` directory
- Consult documentation in docstrings
