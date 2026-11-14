import os, sys, re
from pathlib import Path
sys.path.insert(0, r"D:\Projects\AutoPilot_OS_v2")
from core.blogger_publisher import get_blogger_service
from bs4 import BeautifulSoup

ROOT = Path(r"D:\Projects\AutoPilot_OS_v2")
PENDING = ROOT / "content" / "pending"
PENDING.mkdir(parents=True, exist_ok=True)

post_id = sys.argv[1] if len(sys.argv) > 1 else input("Post ID: ").strip()
service = get_blogger_service()
blog = service.blogs().getByUrl(url='https://dustanddynasty.blogspot.com').execute()
blog_id = blog['id']
post = service.posts().get(blogId=blog_id, postId=post_id, view="AUTHOR", fetchBody=True).execute()
title = post.get('title','')
slug = re.sub(r'[^a-z0-9]+','-', title.lower()).strip('-')[:80] + ".html"
soup = BeautifulSoup(post.get('content',''), 'html.parser')
for img in soup.find_all('img'):
    # remove parent figure if exists
    fig = img.find_parent('div', class_='separator')
    if fig: fig.decompose()
    else: img.decompose()
out = PENDING / slug
out.write_text(str(soup), encoding='utf-8')
print(f"Saved cleaned post to {out}")
# delete from blogger
service.posts().delete(blogId=blog_id, postId=post_id).execute()
print(f"Deleted post {post_id} from Blogger.")
