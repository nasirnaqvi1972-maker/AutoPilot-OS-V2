#!/usr/bin/env python3
"""
add_unmatched_to_master.py - Add unmatched blogger posts to master sites.csv
"""

import csv
import re
from pathlib import Path

MASTER_CSV = Path(r"D:\Projects\AutoPilot_OS_v2\sites.csv")
UNMATCHED_CSV = Path(r"D:\Projects\AutoPilot_OS_v2\topic_lists\unmatched_blogger_posts.csv")

def clean_title(title: str) -> str:
    """Remove subtitle after em-dash, pipe, or colon with space."""
    # Split on em-dash, pipe, or " - " 
    for sep in ['—', '|', ' - ']:
        if sep in title:
            title = title.split(sep)[0]
            break
    # Also handle " | " 
    if ' | ' in title:
        title = title.split(' | ')[0]
    return title.strip()

def load_existing_names(csv_path: Path) -> set:
    """Load existing name_en values from master CSV."""
    names = set()
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get('name_en', '').strip()
            if name:
                names.add(name.lower())
    return names

def get_next_unique_number(csv_path: Path) -> int:
    """Get the next unique_number from master CSV."""
    max_num = 0
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                num = int(row.get('unique_number', 0))
                if num > max_num:
                    max_num = num
            except:
                pass
    return max_num + 1

def main():
    print("[AddToMaster] Loading existing master sites...")
    existing_names = load_existing_names(MASTER_CSV)
    print(f"[AddToMaster] Found {len(existing_names)} existing names")
    
    # Load unmatched blogger posts
    unmatched = []
    with open(UNMATCHED_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            unmatched.append(row)
    
    print(f"[AddToMaster] Found {len(unmatched)} unmatched blogger posts")
    
    # Clean titles and check for duplicates
    new_sites = []
    next_num = get_next_unique_number(MASTER_CSV)
    
    for post in unmatched:
        raw_title = post['blogger_title']
        cleaned = clean_title(raw_title)
        
        # Check if already exists (case-insensitive)
        if cleaned.lower() in existing_names:
            print(f"  [SKIP] Already in master: {cleaned}")
            continue
        
        # Add to new sites
        new_sites.append({
            'unique_number': next_num,
            'id_no': '',
            'rev_bis': '',
            'name_en': cleaned,
            'name_fr': '',
            'name_es': '',
            'name_ru': '',
            'name_ar': '',
            'name_zh': '',
            'short_description_en': '',
            'short_description_fr': '',
            'short_description_es': '',
            'short_description_ru': '',
            'short_description_ar': '',
            'short_description_zh': '',
            'justification_en': '',
            'justification_fr': '',
            'date_inscribed': '',
            'secondary_dates': '',
            'danger': '',
            'date_end': '',
            'danger_list': '',
            'longitude': '',
            'latitude': '',
            'area_hectares': '',
            'C1': '', 'C2': '', 'C3': '', 'C4': '', 'C5': '', 'C6': '',
            'N7': '', 'N8': '', 'N9': '', 'N10': '',
            'criteria_txt': '',
            'category': '',
            'category_short': '',
            'states_name_en': '',
            'states_name_fr': '',
            'states_name_es': '',
            'states_name_ru': '',
            'states_name_ar': '',
            'states_name_zh': '',
            'region_en': '',
            'region_fr': '',
            'iso_code': '',
            'udnp_code': '',
            'transboundary': '',
            'site_name': '',
            'slug': '',
            'category': '',
            'unesco_status': '',
            'year_inscribed': '',
            'country': '',
            'continent': '',
            'latitude': '',
            'longitude': '',
            'criteria': '',
            'area_hectares': '',
            'transboundary': '',
            'language': '',
            'description': '',
        })
        existing_names.add(cleaned.lower())
        next_num += 1
        print(f"  [ADD] {cleaned}")
    
    if not new_sites:
        print("[AddToMaster] No new sites to add")
        return
    
    # Append to master CSV
    fieldnames = list(new_sites[0].keys())
    
    with open(MASTER_CSV, 'a', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writerows(new_sites)
    
    print(f"\n[AddToMaster] Added {len(new_sites)} new sites to {MASTER_CSV}")

if __name__ == "__main__":
    main()