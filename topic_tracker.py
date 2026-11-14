#!/usr/bin/env python3
"""
topic_tracker.py - Track written vs remaining UNESCO sites
Compares master sites.csv against live Blogger posts using fuzzy matching.
"""

import csv
import difflib
import os
import re
import sys
import pickle
from pathlib import Path
from urllib.parse import urlparse

sys.path.append(str(Path(__file__).resolve().parent))
from core.blogger_publisher import get_blogger_service

MASTER_CSV = Path(r"D:\Projects\AutoPilot_OS_v2\sites.csv")
OUTPUT_DIR = Path(r"D:\Projects\AutoPilot_OS_v2\topic_lists")
WRITTEN_CSV = OUTPUT_DIR / "written_posts.csv"
REMAINING_CSV = OUTPUT_DIR / "remaining_topics.csv"

UNMATCHED_CSV = OUTPUT_DIR / "unmatched_blogger_posts.csv"

SIMILARITY_THRESHOLD = 0.75

SUFFIX_WORDS = {
    "unesco", "world", "heritage", "site", "national", "park", "monument",
    "cultural", "natural", "mixed", "archaeological", "historic", "city",
    "town", "region", "landscape", "area", "reserve", "sanctuary",
    "the", "of", "and", "in", "at", "for", "on", "a", "an", "to", "with"
}

def normalize_title(title: str) -> str:
    """Normalize title for fuzzy matching: lowercase, remove special chars, strip suffix words."""
    if not title:
        return ""
    
    # Remove HTML tags
    title = re.sub(r'<[^>]+>', '', title)
    
    # Replace common separators with space
    title = re.sub(r'[—\-\|\:\/\(\)\[\]\{\}]', ' ', title)
    
    # Remove emojis and non-ASCII (keep basic latin)
    title = re.sub(r'[^\x00-\x7F]+', ' ', title)
    
    # Lowercase and split
    words = title.lower().split()
    
    # Filter out suffix words
    filtered = [w for w in words if w not in SUFFIX_WORDS and len(w) > 1]
    
    return ' '.join(filtered)

def load_master_list(csv_path: Path) -> list:
    """Load master sites.csv and extract English names."""
    sites = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get('name_en', '').strip()
            if name:
                sites.append({
                    'master_title': name,
                    'normalized': normalize_title(name),
                    'country': row.get('country', ''),
                    'year_inscribed': row.get('year_inscribed', ''),
                })
    return sites

def fetch_all_blogger_posts() -> list:
    """Fetch ALL posts from Blogger (LIVE and DRAFT)."""
    print("[Tracker] Fetching all Blogger posts...")
    service = get_blogger_service()
    blog = service.blogs().getByUrl(url='https://dustanddynasty.blogspot.com').execute()
    blog_id = blog['id']
    
    all_posts = []
    page_token = None
    while True:
        res = service.posts().list(blogId=blog_id, maxResults=100, pageToken=page_token, fetchBodies=False).execute()
        for p in res.get('items', []):
            all_posts.append({
                'id': p['id'],
                'title': p.get('title', ''),
                'url': p.get('url', ''),
                'status': p.get('status', 'LIVE'),
                'normalized': normalize_title(p.get('title', '')),
            })
        page_token = res.get('nextPageToken')
        if not page_token:
            break
    
    print(f"[Tracker] Found {len(all_posts)} Blogger posts ({sum(1 for p in all_posts if p['status']=='LIVE')} live, {sum(1 for p in all_posts if p['status']=='DRAFT')} draft)")
    return all_posts

def fuzzy_match(master_sites: list, blogger_posts: list) -> tuple:
    """Match master sites to Blogger posts using difflib.SequenceMatcher + containment check."""
    # Build lookup by normalized title for exact matches first
    blogger_by_norm = {}
    for p in blogger_posts:
        blogger_by_norm.setdefault(p['normalized'], []).append(p)
    
    # Track matched blogger post IDs
    matched_blogger_ids = set()
    
    written = []
    remaining = []
    
    for site in master_sites:
        master_norm = site['normalized']
        master_raw_lower = site['master_title'].lower()
        matched = False
        
        # 1. Try exact normalized match
        if master_norm in blogger_by_norm:
            match = blogger_by_norm[master_norm][0]
            matched_blogger_ids.add(match['id'])
            written.append({
                'master_title': site['master_title'],
                'blogger_title': match['title'],
                'post_id': match['id'],
                'blogger_url': match['url'],
                'match_type': 'exact',
                'similarity': 1.0,
            })
            matched = True
        else:
            # 2. Containment check: does blog title contain the UNESCO name?
            # This handles "Acropolis — The Sacred Citadel" vs "Acropolis"
            for p in blogger_posts:
                blog_norm = p['normalized']
                blog_raw_lower = p['title'].lower()
                
                # Check if master is contained in blog (or vice versa for short names)
                if master_norm in blog_norm or master_raw_lower in blog_raw_lower:
                    matched_blogger_ids.add(p['id'])
                    written.append({
                        'master_title': site['master_title'],
                        'blogger_title': p['title'],
                        'post_id': p['id'],
                        'blogger_url': p['url'],
                        'match_type': 'containment',
                        'similarity': 0.95,
                    })
                    matched = True
                    break
        
        if not matched:
            # 3. Fuzzy match on normalized
            best_match = None
            best_score = 0.0
            
            for p in blogger_posts:
                score = difflib.SequenceMatcher(None, master_norm, p['normalized']).ratio()
                if score > best_score:
                    best_score = score
                    best_match = p
            
            if best_score >= SIMILARITY_THRESHOLD:
                matched_blogger_ids.add(best_match['id'])
                written.append({
                    'master_title': site['master_title'],
                    'blogger_title': best_match['title'],
                    'post_id': best_match['id'],
                    'blogger_url': best_match['url'],
                    'match_type': 'fuzzy',
                    'similarity': round(best_score, 3),
                })
                matched = True
        
        if not matched:
            remaining.append({
                'master_title': site['master_title'],
                'country': site['country'],
                'year_inscribed': site['year_inscribed'],
            })
    
    # Find unmatched blogger posts
    unmatched_blogger = [p for p in blogger_posts if p['id'] not in matched_blogger_ids]
    
    return written, remaining, unmatched_blogger

def save_csv(written: list, remaining: list, unmatched_blogger: list):
    """Save written, remaining, and unmatched blogger CSVs."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Written posts
    with open(WRITTEN_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['master_title', 'blogger_title', 'post_id', 'blogger_url', 'match_type', 'similarity'])
        writer.writeheader()
        writer.writerows(written)
    
    # Remaining topics
    with open(REMAINING_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['master_title', 'country', 'year_inscribed'])
        writer.writeheader()
        writer.writerows(remaining)
    
    # Unmatched blogger posts
    with open(UNMATCHED_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['blogger_title', 'post_id', 'blogger_url'])
        writer.writeheader()
        for p in unmatched_blogger:
            writer.writerow({
                'blogger_title': p['title'],
                'post_id': p['id'],
                'blogger_url': p['url'],
            })
    
    print(f"[Tracker] Saved: {WRITTEN_CSV}")
    print(f"[Tracker] Saved: {REMAINING_CSV}")
    print(f"[Tracker] Saved: {UNMATCHED_CSV}")

def main():
    print("[Tracker] Starting topic tracking...")
    
    # 1. Load master list
    master_sites = load_master_list(MASTER_CSV)
    print(f"[Tracker] Loaded {len(master_sites)} sites from master list")
    
    # 2. Fetch all Blogger posts
    blogger_posts = fetch_all_blogger_posts()
    
    # 3. Fuzzy match
    written, remaining, unmatched_blogger = fuzzy_match(master_sites, blogger_posts)
    
    # 4. Save
    save_csv(written, remaining, unmatched_blogger)
    
    # 5. Summary
    print(f"\n[Tracker] Found {len(written)} written posts. {len(remaining)} topics remaining. {len(unmatched_blogger)} unmatched Blogger posts.")
    
    # Show match types
    exact = sum(1 for w in written if w['match_type'] == 'exact')
    containment = sum(1 for w in written if w['match_type'] == 'containment')
    fuzzy = sum(1 for w in written if w['match_type'] == 'fuzzy')
    print(f"  Exact matches: {exact}")
    print(f"  Containment matches: {containment}")
    print(f"  Fuzzy matches (>75%): {fuzzy}")
    
    if remaining:
        print(f"\nFirst 10 remaining:")
        for r in remaining[:10]:
            print(f"  - {r['master_title']} ({r['country']})")
    
    if unmatched_blogger:
        print(f"\nUnmatched Blogger posts (first 10):")
        for p in unmatched_blogger[:10]:
            print(f"  - {p['title'][:80]}")

if __name__ == "__main__":
    main()