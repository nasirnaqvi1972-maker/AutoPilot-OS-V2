import sys
import io
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import csv
import datetime
from pathlib import Path
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core.blogger_publisher import get_blogger_service

V2_ROOT = Path(__file__).resolve().parent


def fetch_all(service, blog_id, status):
    posts = []
    tok = None
    while True:
        res = service.posts().list(blogId=blog_id, status=status, maxResults=100, pageToken=tok).execute()
        posts.extend(res.get('items', []))
        tok = res.get('nextPageToken')
        if not tok:
            break
    return posts


def main():
    service = get_blogger_service()
    blog = service.blogs().getByUrl(url='https://dustanddynasty.blogspot.com').execute()
    blog_id = blog['id']

    all_posts = []
    for status in ('LIVE', 'DRAFT'):
        all_posts.extend(fetch_all(service, blog_id, status))

    rows = []
    for p in all_posts:
        full = service.posts().get(blogId=blog_id, postId=p['id'], view='AUTHOR', fetchBody=True).execute()
        soup = BeautifulSoup(full.get('content', ''), 'html.parser')

        img_count = len(soup.find_all('img'))
        h2_count = len(soup.find_all('h2'))
        text = soup.get_text(" ", strip=True)
        word_count = len(text.split())
        has_link = any('dustanddynasty.blogspot.com' in (a.get('href') or '') for a in soup.find_all('a'))

        missing = []
        if img_count < 7:
            missing.append(f"Images({img_count}<7)")
        if h2_count < 2:
            missing.append(f"H2({h2_count}<2)")
        if word_count < 2500:
            missing.append(f"Words({word_count}<2500)")
        if not has_link:
            missing.append("Interlink")

        if missing:
            rows.append({
                'Title': full.get('title', ''),
                'Post ID': full.get('id', ''),
                'URL': full.get('url', ''),
                'Image Count': img_count,
                'H2 Count': h2_count,
                'Word Count': word_count,
                'Missing Elements': "; ".join(missing),
            })

    audit_dir = V2_ROOT / "pattern_audits"
    audit_dir.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    csv_path = audit_dir / f"pattern_audit_{timestamp}.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['Title', 'Post ID', 'URL', 'Image Count', 'H2 Count', 'Word Count', 'Missing Elements'])
        writer.writeheader()
        writer.writerows(rows)

    print(f"[Audit] Found {len(rows)} posts failing pattern. Report saved to pattern_audits/pattern_audit_{timestamp}.csv")


if __name__ == "__main__":
    main()
