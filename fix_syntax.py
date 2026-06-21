# Read the file and fix the syntax error
with open('rules_engine/fix_actions.py', 'r') as f:
    content = f.read()

# Find and replace the problematic section
old_section = '''    if best_parsed is not None and best_count > 0:
        # Only update where original was not null AND we successfully parsed
        mask = (original_col.notna()) & (best_parsed.notna())
        df.loc[mask, column] = best_parsed.loc[mask].astype(str)
        logger.info(f"Standardized {mask.sum()} date values in {column}")
    else:
        # Could not parse reliably, keep original format
        logger.info(f"Could not reliably parse dates in {column}, keeping original format")
        logger.info(f"Parsed {final.notna().sum()} dates in {column} using multi-strategy parsing")
    else:
        logger.info(f"No dates parsed for {column}; leaving values unchanged")

    return df'''

new_section = '''    if best_parsed is not None and best_count > 0:
        # Only update where original was not null AND we successfully parsed
        mask = (original_col.notna()) & (best_parsed.notna())
        df.loc[mask, column] = best_parsed.loc[mask].astype(str)
        logger.info(f"Standardized {mask.sum()} date values in {column}")
    else:
        # Could not parse reliably, keep original format
        logger.info(f"Could not reliably parse dates in {column}, keeping original format")

    return df'''

content = content.replace(old_section, new_section)

with open('rules_engine/fix_actions.py', 'w') as f:
    f.write(content)

print("Fixed syntax error in fix_actions.py")
