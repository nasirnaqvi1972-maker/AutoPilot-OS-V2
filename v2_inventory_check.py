import json
import csv
import time
import sys
from datetime import datetime
from pathlib import Path
from googleapiclient.errors import HttpError
from core.blogger_publisher import get_blogger_service

BLOG_URL = "https://dustanddynasty.blogspot.com"
REPORTS_DIR = Path("reports")
OUTPUT_TMP = Path("verified_inventory.tmp")
OUTPUT_JSON = Path("verified_inventory.json")

def get_latest_csv():
    csv_files = sorted(REPORTS_DIR.glob("content_audit_*.csv"))
    if not csv_files:
        print("ERROR: No content_audit CSV found in reports/")
        sys.exit(1)
    return csv_files[-1] 

def fetch_live_posts_with_retry(service, blog_id, max_retries=3):
    print("Fetching live posts from Blogger API...")
    posts = {}
    tok = None
    
    while True:
        retries = 0
        while retries < max_retries:
            try:
                res = service.posts().list(
                    blogId=blog_id, 
                    status='LIVE', 
                    maxResults=50, 
                    pageToken=tok
                ).execute()
                break 
            except HttpError as e:
                retries += 1
                print(f"API Error (Attempt {retries}/{max_retries}): {e}")
                if retries >= max_retries:
                    print("CRITICAL: Max retries reached. Aborting to prevent partial inventory.")
                    sys.exit(1)
                time.sleep(2 ** retries)
        
        for item in res.get('items', []):
            posts[item['id']] = {
                "title": item.get('title', 'Untitled'),
                "url": item.get('url', '')
            }
        
        tok = res.get('nextPageToken')
        if not tok:
            break
            
    return posts

def main():
    csv_path = get_latest_csv()
    print(f"Using CSV file: {csv_path}")
    
    print("Connecting to Blogger API...")
    service = get_blogger_service()
    blog = service.blogs().getByUrl(url=BLOG_URL).execute()
    blog_id = blog['id']

    live_posts = fetch_live_posts_with_retry(service, blog_id)
    
    csv_posts = {}
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            csv_posts[row['id']] = {
                "title": row['title'],
                "url": row['url']
            }

    print("\n--- RECONCILIATION REPORT ---")
    print(f"Live Blogger Posts: {len(live_posts)}")
    print(f"CSV Audit Posts:    {len(csv_posts)}")

    live_only = set(live_posts.keys()) - set(csv_posts.keys())
    csv_only = set(csv_posts.keys()) - set(live_posts.keys())
    
    title_mismatches = 0
    for pid in set(live_posts.keys()) & set(csv_posts.keys()):
        if live_posts[pid]['title'].strip() != csv_posts[pid]['title'].strip():
            title_mismatches += 1

    if live_only:
        print(f"\n[WARNING] {len(live_only)} posts are LIVE but missing from the CSV:")
        for pid in list(live_only)[:5]:
            print(f"  - {live_posts[pid]['title']} (ID: {pid})")
            
    if csv_only:
        print(f"\n[WARNING] {len(csv_only)} posts are in the CSV but NOT LIVE on Blogger:")
        for pid in list(csv_only)[:5]:
            print(f"  - {csv_posts[pid]['title']} (ID: {pid})")
            
    if title_mismatches > 0:
        print(f"\n[WARNING] {title_mismatches} posts have different titles in the Live site vs CSV.")

    if not live_only and not csv_only:
        print("\n[OK] Perfect match! Every post in the CSV exists on the live site.")

    inventory_data = {
        "metadata": {
            "blog_id": blog_id,
            "generated_at": datetime.now().isoformat(),
            "total_live": len(live_posts),
            "total_csv": len(csv_posts)
        },
        "posts": live_posts
    }

    print(f"\nSaving inventory safely to {OUTPUT_JSON}...")
    with open(OUTPUT_TMP, 'w', encoding='utf-8') as f:
        json.dump(inventory_data, f, indent=2)
    
    OUTPUT_TMP.replace(OUTPUT_JSON)
    print("SUCCESS! No live posts were modified. Inventory verified.")

if __name__ == "__main__":
    main()