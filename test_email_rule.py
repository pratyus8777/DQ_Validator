import subprocess
import sys

result = subprocess.run([sys.executable, 'assessment_first_pipeline.py', '--clean'], 
                       capture_output=True, text=True, timeout=120)

output = result.stderr + result.stdout

for line in output.split('\n'):
    if 'email' in line.lower() or 'uppercase' in line.lower():
        print(line)
