import os, sys, re
sys.path.insert(0, r"D:\Projects\AutoPilot_OS_v2")
from core.blogger_publisher import get_blogger_service
from bs4 import BeautifulSoup

service = get_blogger_service()
blog = service.blogs().getByUrl(url='https://dustanddynasty.blogspot.com').execute()
blog_id = blog['id']

drafts = service.posts().list(blogId=blog_id, status='DRAFT', maxResults=50).execute().get('items', [])

def norm(t):
    t = t.replace('â€”','—').replace('Ã­','í')
    return re.sub(r'\s+',' ', t).strip().lower()

groups = {}
for d in drafts:
    groups.setdefault(norm(d.get('title','')), []).append(d)

for title, items in groups.items():
    if len(items) <= 1:
        continue
    # keep most recent by published/updated
    items_sorted = sorted(items, key=lambda x: x.get('updated',''), reverse=True)
    keep = items_sorted[0]
    for dup in items_sorted[1:]:
        service.posts().delete(blogId=blog_id, postId=dup['id']).execute()
        print(f"Deleted duplicate draft: {dup.get('title')} ({dup['id']})")
    # fix encoding on kept
    full = service.posts().get(blogId=blog_id, postId=keep['id'], view="AUTHOR", fetchBody=True).execute()
    soup = BeautifulSoup(full.get('content',''), 'html.parser')
    text = str(soup).replace('â€”','—').replace('Ã­','í')
    new_title = keep.get('title','').replace('â€”','—').replace('Ã­','í')
    body = {'id': keep['id'], 'title': new_title, 'content': text}
    if full.get('searchDescription'):
        body['searchDescription'] = full['searchDescription'].replace('â€”','—').replace('Ã­','í')
    if keep.get('labels'):
        body['labels'] = keep['labels']
    service.posts().patch(blogId=blog_id, postId=keep['id'], body=body).execute()
    print(f"Fixed encoding for: {new_title}")

print("Cleanup complete.")
