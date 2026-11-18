import sys
import io
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import csv
import re
from pathlib import Path
from bs4 import BeautifulSoup

sys.path.insert(0, r"D:\Projects\AutoPilot_OS_v2")
from core.blogger_publisher import get_blogger_service

V2_ROOT = Path(r"D:\Projects\AutoPilot_OS_v2")
PENDING_DIR = V2_ROOT / "content" / "pending"
PENDING_DIR.mkdir(parents=True, exist_ok=True)


def slugify(title):
    s = re.sub(r'[^a-zA-Z0-9]+', '-', title).strip('-').lower()
    return s or "post"


def main():
    audit_dir = V2_ROOT / "pattern_audits"
    csvs = sorted(audit_dir.glob("pattern_audit_*.csv"))
    if not csvs:
        print("No audit CSV found.")
        return
    latest = csvs[-1]
    print(f"Using audit file: {latest}")

    service = get_blogger_service()
    blog = service.blogs().getByUrl(url='https://dustanddynasty.blogspot.com').execute()
    blog_id = blog['id']

    post_ids = []
    with open(latest, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            post_ids.append(row['Post ID'])

    saved = 0
    for pid in post_ids:
        try:
            full = service.posts().get(blogId=blog_id, postId=pid, view='AUTHOR', fetchBody=True).execute()
        except Exception as e:
            print(f"[ERR] {pid}: {e}")
            continue
        title = full.get('title', '')
        content = full.get('content', '')
        soup = BeautifulSoup(content, 'html.parser')
        for tag in soup.find_all('img'):
            tag.decompose()
        for tag in soup.find_all('iframe'):
            src = tag.get('src', '').lower()
            if ('google.com/maps' not in src and 'google.com/maps/embed' not in src 
                and 'youtube.com/embed' not in src and 'youtube-nocookie.com/embed' not in src):
                tag.decompose()
        for tag in soup.find_all('div', class_='separator'):
            tag.decompose()
        cleaned = str(soup)
        # ensure h1 title present
        if not soup.find('h1'):
            h1 = soup.new_tag('h1')
            h1.string = title
            soup.insert(0, h1)
            cleaned = str(soup)

        out_path = PENDING_DIR / f"{slugify(title)}.html"
        out_path.write_text(cleaned, encoding='utf-8')
        saved += 1
        print(f"[PULL] Saved {title} to pending.")

    print(f"\nTotal saved to pending: {saved}")


if __name__ == "__main__":
    main()
