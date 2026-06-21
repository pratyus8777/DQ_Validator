import subprocess
import re

# Run the cleansing and capture full output
result = subprocess.run(
    ['python', 'assessment_first_pipeline.py', '--clean', '--dedup-method', 'keep-first'],
    capture_output=True,
    text=True
)

output = result.stdout + result.stderr

# Find the rule merge section
if 'RULE MERGE STRATEGY' in output:
    print("\n" + "="*80)
    print("RULE MERGE STRATEGY SECTION")
    print("="*80)
    
    # Extract lines between markers
    start = output.find('RULE MERGE STRATEGY')
    end = output.find('Transformations by column', start)
    
    if start >= 0 and end >= 0:
        section = output[start:end]
        print(section)
    
    # Count rules
    db_match = re.search(r'Database rules loaded: (\d+)', output)
    dashboard_match = re.search(r'Dashboard rules loaded: (\d+)', output)
    total_match = re.search(r'Total rules after merge: (\d+)', output)
    
    if db_match:
        print(f"\nDatabase rules: {db_match.group(1)}")
    if dashboard_match:
        print(f"Dashboard rules: {dashboard_match.group(1)}")
    if total_match:
        print(f"Total rules after merge: {total_match.group(1)}")
else:
    print("No rule merge section found - checking if rules were loaded")
    if 'Using' in output:
        lines = output.split('\n')
        for line in lines:
            if 'Using' in line and 'rules' in line.lower():
                print(line)
