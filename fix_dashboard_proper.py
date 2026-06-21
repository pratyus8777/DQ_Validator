#!/usr/bin/env python3
"""Properly convert dashboard_final_backup.py to ASCII-safe version"""

# Read the backup file
with open('dashboard_final_backup.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Process line by line to avoid breaking string structures
cleaned_lines = []
for line in lines:
    # Replace emojis/Unicode with ASCII equivalents
    # Keep spacing and structure intact
    line = line.replace('→', '->')
    line = line.replace('✓', '[OK]')
    line = line.replace('✅', '[DONE]')
    line = line.replace('📊', '[CHART]')
    line = line.replace('🏆', '[TROPHY]')
    line = line.replace('⚡', '[FAST]')
    line = line.replace('🧠', '[BRAIN]')
    line = line.replace('📋', '[LIST]')
    line = line.replace('🎯', '[TARGET]')
    line = line.replace('💰', '[MONEY]')
    line = line.replace('🔤', '[TEXT]')
    line = line.replace('🆔', '[ID]')
    line = line.replace('📤', '[UPLOAD]')
    line = line.replace('💾', '[SAVE]')
    line = line.replace('🔄', '[RESET]')
    line = line.replace('🧹', '[CLEAN]')
    line = line.replace('📥', '[DOWNLOAD]')
    line = line.replace('⏳', '[WAIT]')
    line = line.replace('⚠️', '[WARN]')
    line = line.replace('🔂', '[PROCESS]')
    line = line.replace('📈', '[GROWTH]')
    line = line.replace('🎨', '[STYLE]')
    line = line.replace('💡', '[IDEA]')
    line = line.replace('🚀', '[ROCKET]')
    line = line.replace('❌', '[ERROR]')
    
    cleaned_lines.append(line)

# Write the cleaned file
with open('dashboard_final.py', 'w', encoding='utf-8') as f:
    f.writelines(cleaned_lines)

print('Dashboard file fixed successfully')
print(f'Total lines processed: {len(cleaned_lines)}')
