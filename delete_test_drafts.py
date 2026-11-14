#!/usr/bin/env python3
"""
Delete test drafts from Blogger API
"""

import sys
sys.path.append(r'D:\Projects\AutoPilot_OS_v2')
from core.blogger_publisher import get_blogger_service

service = get_blogger_service()
blog = service.blogs().getByUrl(url='https://dustanddynasty.blogspot.com').execute()
blog_id = blog['id']

# Search for drafts with these titles
target_titles = [
    "Lower Valley of the Omo",
    "Rock-Hewn Churches of Lalibela"
]

for target in target_titles:
    target_norm = target.strip().lower()
    page_token = None
    found = False
    while True:
        res = service.posts().list(blogId=blog_id, maxResults=100, pageToken=page_token, status='DRAFT').execute()
        for post in res.get('items', []):
            if post.get('title', '').strip().lower() == target_norm:
                post_id = post['id']
                print(f"Deleting draft: {target} (ID: {post_id})")
                service.posts().delete(blogId=blog_id, postId=post_id).execute()
                found = True
        page_token = res.get('nextPageToken')
        if not page_token:
            break
    if not found:
        print(f"No draft found for: {target}")

print("Done.")