# Read the backup file as UTF-8
with open('dashboard_final_backup.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace problem characters in triple-quoted Python strings
replacements = [
    ('1. ✓ Assessment', '1. (DONE) Assessment'),
    ('2. ✓ Reviewed', '2. (DONE) Reviewed'),
    ('3. ✓ Defined', '3. (DONE) Defined'),
    ('4. → **Execute', '4. --> **Execute'),
    ('5. → View', '5. --> View'),
]

for old, new in replacements:
    content = content.replace(old, new)

# Write with UTF-8
with open('dashboard_final.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Dashboard fixed')
