import csv
import re
from pathlib import Path

SRC = Path(r"D:\Projects\AutoPilot_OS_v2\sites.csv")
DST = Path(r"D:\Projects\AutoPilot_OS_v2\sites.csv.cleaned")

def strip_html(text: str) -> str:
    """Strip all HTML tags from text."""
    if not text:
        return text
    # Use regex to remove all HTML tags
    clean = re.sub(r'<[^>]+>', '', text)
    # Clean up extra whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

with open(SRC, 'r', encoding='utf-8', newline='') as f_in:
    reader = csv.DictReader(f_in)
    fieldnames = reader.fieldnames
    rows = list(reader)

print(f"Read {len(rows)} rows")

# Clean the site_name column (and others if needed)
cleaned_count = 0
for row in rows:
    if 'site_name' in row:
        original = row['site_name']
        cleaned = strip_html(original)
        if original != cleaned:
            row['site_name'] = cleaned
            cleaned_count += 1
            print(f"  CLEANED: {original[:80]} -> {cleaned[:80]}")

# Also clean other text columns that might have HTML
text_columns = ['name_en', 'name_fr', 'name_es', 'short_description_en', 'justification_en', 'description']
for col in text_columns:
    if col in fieldnames:
        for row in rows:
            if row.get(col):
                original = row[col]
                cleaned = strip_html(original)
                if original != cleaned:
                    row[col] = cleaned

print(f"Cleaned {cleaned_count} site_name entries")

# Write cleaned CSV
with open(DST, 'w', encoding='utf-8', newline='') as f_out:
    writer = csv.DictWriter(f_out, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"Written to {DST}")

# Replace original
import shutil
shutil.move(str(DST), str(SRC))
print("Original sites.csv replaced with cleaned version.")