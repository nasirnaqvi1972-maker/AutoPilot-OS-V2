import os
import sys
import json
import time
import re
from datetime import datetime
from bs4 import BeautifulSoup

sys.path.insert(0, r"D:\Projects\AutoPilot_OS_v2")
from core.blogger_publisher import get_blogger_service

DRY_RUN = True   # Set to False only after dry run confirmed

# Short slug -> substring of the matching post title (used to find real post URL)
REPAIR_MAP = {
    "grand-canyon-national-park": "Grand Canyon National Park",
    "kluane-wrangell-st-elias":   "Kluane / Wrangell-St. Elias",
    "mesa-verde":                 "Mesa Verde National Park",
    "nahanni-national-park":      "Nahanni National Park",
    "taj-mahal":                  "Taj Mahal",
    "yellowstone-national-park":  "Yellowstone National Park",
}

def run_repair():
    service = get_blogger_service()
    blog = service.blogs().getByUrl(url='https://dustanddynasty.blogspot.com').execute()
    blog_id = blog['id']

    print("Fetching all posts to map titles -> real URLs...")
    all_posts = []
    tok = None
    while True:
        res = service.posts().list(blogId=blog_id, maxResults=100, pageToken=tok).execute()
        all_posts.extend(res.get('items', []))
        tok = res.get('nextPageToken')
        if not tok: break

    print(f"Total posts: {len(all_posts)}")

    # Build slug -> real URL map
    url_map = {}
    for short_slug, title_fragment in REPAIR_MAP.items():
        hit = next((p for p in all_posts if title_fragment.lower() in p.get('title', '').lower()), None)
        if hit and 'url' in hit:
            url_map[short_slug] = hit['url']
            print(f"  OK  {short_slug}  ->  {hit['url']}")
        else:
            print(f"  MISS  {short_slug}  (no matching post found)")

    if not url_map:
        print("No repairable links found. Aborting.")
        return

    print("\nScanning posts for links to repair...")
    fixed_count = 0

    for i, p in enumerate(all_posts, 1):
        try:
            full = service.posts().get(blogId=blog_id, postId=p['id'], view="AUTHOR", fetchBody=True).execute()
            html = full.get('content', '')
            soup = BeautifulSoup(html, 'html.parser')
            changed = False

            for a in soup.find_all('a', href=True):
                href = a['href'].rstrip('/')
                # Strip any absolute prefix to compare on slug only
                for short_slug, real_url in url_map.items():
                    if href.endswith('/' + short_slug):
                        print(f"  [{i}] {p.get('title','')[:50]}")
                        print(f"       OLD: {a['href']}")
                        print(f"       NEW: {real_url}")
                        a['href'] = real_url
                        changed = True
                        fixed_count += 1
                        break

            if changed and not DRY_RUN:
                body = {
                    'id': p['id'],
                    'title': p.get('title'),
                    'content': str(soup),
                }
                if full.get('searchDescription'):
                    body['searchDescription'] = full['searchDescription']
                if p.get('labels'):
                    body['labels'] = p['labels']
                service.posts().patch(blogId=blog_id, postId=p['id'], body=body).execute()
                print(f"       PATCHED")
                time.sleep(0.3)
            elif changed and DRY_RUN:
                print(f"       [DRY RUN] would patch")

        except Exception as e:
            print(f"  ERROR on {p.get('title','')[:40]}: {e}")

    print("=" * 50)
    print(f"LINK REPAIR COMPLETE — {'DRY RUN' if DRY_RUN else 'LIVE'}")
    print(f"  Links {'would be ' if DRY_RUN else ''}repaired: {fixed_count}")
    print("=" * 50)

if __name__ == "__main__":
    run_repair()
