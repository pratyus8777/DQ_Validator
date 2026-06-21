import pandas as pd
from data_io.local_source import LocalDataSource

source = LocalDataSource()
df = source.read_sample_data()
print(f'Original data: {len(df)} records')
print(f'First row policy: {df.iloc[0]["Policy Number"]}')

# Check if there's a reduction in the final_clean stage
import sys
sys.path.insert(0, '.')

from cli import SemanticDQPipeline
pipeline = SemanticDQPipeline("config/local.yaml")
print(f"\nData after ingest: {len(pipeline.context['data'])} records")
