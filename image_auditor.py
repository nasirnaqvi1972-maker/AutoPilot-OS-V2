import os
import sys
import io
import csv
import datetime
from pathlib import Path
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core.blogger_publisher import get_blogger_service

# Force UTF-8 output
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

V2_ROOT = Path(__file__).resolve().parent

def run_audit():
    audit_dir = V2_ROOT / "image_audits"
    audit_dir.mkdir(parents=True, exist_ok=True)
    service = get_blogger_service()
    blog = service.blogs().getByUrl(url='https://dustanddynasty.blogspot.com').execute()
    blog_id = blog['id']

    print("Fetching all posts...")
    all_posts = []
    tok = None
    while True:
        res = service.posts().list(blogId=blog_id, maxResults=100, pageToken=tok).execute()
        all_posts.extend(res.get('items', []))
        tok = res.get('nextPageToken')
        if not tok: break

    print(f"Found {len(all_posts)} total posts. Checking for images...")

    missing_images = []

    for i, p in enumerate(all_posts, 1):
        try:
            # Fetch full content
            full = service.posts().get(blogId=blog_id, postId=p['id'], view="AUTHOR", fetchBody=True).execute()
            html = full.get('content', '')

            if not html:
                missing_images.append((p.get('title', ''), p['id'], p.get('url', '')))
                continue

            soup = BeautifulSoup(html, 'html.parser')

            # Count images, iframes, and background images
            img_count = len(soup.find_all('img'))
            iframe_count = len(soup.find_all('iframe'))

            if img_count == 0 and iframe_count == 0:
                missing_images.append((p.get('title', ''), p['id'], p.get('url', '')))
                print(f"  [MISSING] {p.get('title', '')[:50]}")

        except Exception as e:
            print(f"  [ERROR] Post {p['id']}: {e}")

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_path = audit_dir / f"missing_images_{timestamp}.csv"

    with open(report_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["title", "post_id", "url"])
        for title, pid, url in missing_images:
            # Strip BOM and Mojibake
            clean_title = title.replace('﻿', '').replace('â€”', '—')
            writer.writerow([clean_title, pid, url])

    print("==================================================")
    print(f"[Audit] Found {len(missing_images)} posts with 0 images.")
    print(f"Report saved to: {report_path}")
    print("==================================================")

if __name__ == "__main__":
    run_audit()
