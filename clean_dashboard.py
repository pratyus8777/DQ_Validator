#!/usr/bin/env python
import re

# Read original file
with open('dashboard_final_backup.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove ALL non-ASCII characters except newlines, tabs, and spaces
# Keep printable ASCII (32-126) plus newline (10), tab (9), carriage return (13)
def is_ascii_safe(char):
    code = ord(char)
    return (32 <= code <= 126) or code in (9, 10, 13)

cleaned = ''.join(char if is_ascii_safe(char) else '?' for char in content)

# Write to new file
with open('dashboard_final.py', 'w', encoding='utf-8') as f:
    f.write(cleaned)

print('Dashboard cleaned: all non-ASCII characters removed')
