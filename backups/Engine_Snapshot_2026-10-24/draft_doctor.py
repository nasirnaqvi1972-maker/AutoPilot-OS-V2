import sys
import io
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import os, sys, re
sys.path.insert(0, r"D:\Projects\AutoPilot_OS_v2")
from core.blogger_publisher import get_blogger_service
from bs4 import BeautifulSoup
sys.path.insert(0, r"D:\Projects\AutoPilot_OS_v2")
from location_detector import detect_location

service = get_blogger_service()
blog = service.blogs().getByUrl(url='https://dustanddynasty.blogspot.com').execute()
blog_id = blog['id']

target_id = sys.argv[1] if len(sys.argv) > 1 else None

def fetch_drafts():
    drafts = []
    tok = None
    while True:
        res = service.posts().list(blogId=blog_id, status='DRAFT', maxResults=50, pageToken=tok).execute()
        drafts.extend(res.get('items', []))
        tok = res.get('nextPageToken')
        if not tok: break
    return drafts

def fix_post(post):
    post_id = post['id']
    full = service.posts().get(blogId=blog_id, postId=post_id, view="AUTHOR", fetchBody=True).execute()
    soup = BeautifulSoup(full.get('content',''), 'html.parser')
    changed = False
    issues = []

    imgs = soup.find_all('img')
    if len(imgs) != 7:
        print(f"  [WARNING] Draft has {len(imgs)} images (need 7).")
    # meta description
    meta = full.get('searchDescription', '')
    if not meta:
        first_p = soup.find('p')
        if first_p:
            text = first_p.get_text(" ", strip=True)
            clean = re.sub(r'\s+',' ', text)
            if len(clean) > 150:
                clean = clean[:147].rsplit(' ',1)[0] + "..."
            meta = clean
            changed = True
            issues.append("generated meta description")

    # H1 demote
    h1s = soup.find_all('h1')
    if len(h1s) > 1:
        for extra in h1s[1:]:
            extra.name = 'h2'
        changed = True
        issues.append("demoted extra H1 to H2")

    # jump break
    if '<!--more-->' not in str(soup):
        first_p = soup.find('p')
        if first_p:
            more = BeautifulSoup('<!--more-->', 'html.parser')
            first_p.insert_after(more)
            changed = True
            issues.append("injected jump break")

    # alt text
    for img in soup.find_all('img'):
        if not img.get('alt'):
            img['alt'] = (post.get('title','')[:80])
            changed = True
            issues.append("added missing alt")

    labels = list(post.get('labels', []) or [])
    detected = detect_location(post.get('title',''), str(soup))
    for lab in detected:
        if lab not in labels:
            labels.append(lab)
    if changed or detected:
        body = {'id': post_id, 'title': post.get('title'), 'content': str(soup), 'searchDescription': meta, 'labels': labels}
        service.posts().patch(blogId=blog_id, postId=post_id, body=body).execute()
        print(f"  Fixed draft '{post.get('title','')[:40]}': {', '.join(issues)}")
    else:
        print(f"  OK draft '{post.get('title','')[:40]}': no issues")

def main():
    if target_id:
        post = service.posts().get(blogId=blog_id, postId=target_id, view="AUTHOR", fetchBody=True).execute()
        fix_post(post)
    else:
        drafts = fetch_drafts()
        print(f"Found {len(drafts)} drafts.")
        for d in drafts:
            fix_post(d)
    print("Draft doctor complete.")

if __name__ == "__main__":
    main()
