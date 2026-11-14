import os, sys, re
sys.path.insert(0, r"D:\Projects\AutoPilot_OS_v2")
from core.blogger_publisher import get_blogger_service
from bs4 import BeautifulSoup
from pathlib import Path

ROOT = Path(r"D:\Projects\AutoPilot_OS_v2")
PENDING = ROOT / "content" / "pending"
PENDING.mkdir(parents=True, exist_ok=True)
service = get_blogger_service()
blog = service.blogs().getByUrl(url='https://dustanddynasty.blogspot.com').execute()
blog_id = blog['id']
drafts = service.posts().list(blogId=blog_id, status='DRAFT', maxResults=50).execute().get('items', [])
targets = ["avignon", "porto", "blenheim"]
for d in drafts:
    title = d.get('title','')
    if not any(t in title.lower() for t in targets):
        continue
    slug = re.sub(r'[^a-z0-9]+','-', title.lower()).strip('-')[:80] + ".html"
    soup = BeautifulSoup(d.get('content',''), 'html.parser')
    for img in soup.find_all('img'):
        fig = img.find_parent('div', class_='separator')
        if fig: fig.decompose()
        else: img.decompose()
    # ensure title/meta
    if not soup.find('title'):
        t = soup.new_tag('title'); t.string = title
        head = soup.new_tag('head'); head.append(t); soup.insert(0, head)
    if not soup.find('meta', attrs={'name':'description'}):
        meta = soup.new_tag('meta', attrs={'name':'description','content': title[:150]})
        if soup.head: soup.head.append(meta)
    out = PENDING / slug
    out.write_text(str(soup), encoding='utf-8')
    print(f"[PULL] Saved {slug} to pending (images removed).")
print("Done.")
