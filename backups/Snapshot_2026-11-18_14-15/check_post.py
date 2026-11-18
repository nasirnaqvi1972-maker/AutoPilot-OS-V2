#!/usr/bin/env python3
"""
Check if post exists on Blogger
"""

import sys
sys.path.append(r'D:\Projects\AutoPilot_OS_v2')
from core.blogger_publisher import get_blogger_service

service = get_blogger_service()
blog = service.blogs().getByUrl(url='https://dustanddynasty.blogspot.com').execute()
blog_id = blog['id']

# Search for the post
target = "Lower Valley of the Omo"
target_norm = target.strip().lower()
page_token = None
found = False
while True:
    res = service.posts().list(blogId=blog_id, maxResults=100, pageToken=page_token, status='DRAFT').execute()
    for post in res.get('items', []):
        if post.get('title', '').strip().lower() == target_norm:
            print(f"Found DRAFT: {post['title']} (ID: {post['id']})")
            print(f"URL: {post['url']}")
            found = True
    page_token = res.get('nextPageToken')
    if not page_token:
        break

# Also check live posts
page_token = None
while True:
    res = service.posts().list(blogId=blog_id, maxResults=100, pageToken=page_token, status='LIVE').execute()
    for post in res.get('items', []):
        if post.get('title', '').strip().lower() == target_norm:
            print(f"Found LIVE: {post['title']} (ID: {post['id']})")
            print(f"URL: {post['url']}")
            found = True
    page_token = res.get('nextPageToken')
    if not page_token:
        break

if not found:
    print(f"Not found on Blogger: {target}")