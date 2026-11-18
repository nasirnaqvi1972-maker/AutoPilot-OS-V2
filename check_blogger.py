import sys
sys.path.insert(0, r'D:\Projects\AutoPilot_OS_v2')
from core.blogger_publisher import get_blogger_service

service = get_blogger_service()
blog = service.blogs().getByUrl(url='https://dustanddynasty.blogspot.com').execute()
blog_id = blog['id']

res = service.posts().list(blogId=blog_id, status='DRAFT', maxResults=10).execute()
for p in res.get('items', []):
    title = p.get('title', '')[:80]
    print(f'DRAFT: {title} (ID: {p["id"]})')

res = service.posts().list(blogId=blog_id, status='LIVE', maxResults=5).execute()
for p in res.get('items', []):
    title = p.get('title', '')[:80]
    print(f'LIVE: {title} (ID: {p["id"]})')