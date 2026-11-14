import os, sys, re
from pathlib import Path
sys.path.insert(0, r"D:\Projects\AutoPilot_OS_v2")
from core.blogger_publisher import get_blogger_service
from bs4 import BeautifulSoup

ROOT = Path(r"D:\Projects\AutoPilot_OS_v2")
PENDING = ROOT / "content" / "pending"
PENDING.mkdir(parents=True, exist_ok=True)

service = get_blogger_service()
blog = service.blogs().getByUrl(url='https://dustanddynasty.blogspot.com').execute()
blog_id = blog['id']

drafts = []
tok = None
while True:
    res = service.posts().list(blogId=blog_id, status='DRAFT', maxResults=20, pageToken=tok).execute()
    drafts.extend(res.get('items', []))
    tok = res.get('nextPageToken')
    if not tok: break

print(f"Found {len(drafts)} drafts.")
for d in drafts:
    title = d.get('title','Untitled')
    slug = re.sub(r'[^a-z0-9]+','-', title.lower()).strip('-')[:80] + ".html"
    soup = BeautifulSoup(d.get('content',''), 'html.parser')
    if not soup.find('title'):
        t = soup.new_tag('title')
        t.string = title
        if soup.head:
            soup.head.append(t)
        else:
            head = soup.new_tag('head')
            head.append(t)
            soup.insert(0, head)
    if not soup.find('meta', attrs={'name':'description'}):
        meta = soup.new_tag('meta', attrs={'name':'description','content': title[:150]})
        if soup.head:
            soup.head.append(meta)
    out = PENDING / slug
    out.write_text(str(soup), encoding='utf-8')
    print(f"[PULL] Saved {slug} to pending.")
print("Done.")
