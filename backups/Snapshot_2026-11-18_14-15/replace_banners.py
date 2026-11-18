#!/usr/bin/env python3
"""
replace_banners.py - Replace legacy support banners with new template across all Blogger posts
"""

import sys
import io
import time
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
sys.path.insert(0, r"D:\Projects\AutoPilot_OS_v2")
from core.blogger_publisher import get_blogger_service
from bs4 import BeautifulSoup

NEW_BANNER_HTML = '''
<div class="sidebar-support-banner post-support-banner">
  <h3>🌍 Support Dust and Dynasty</h3>
  <p>Your support funds the research and hosting that keeps this encyclopedia free for everyone.</p>
  <div class="sidebar-button-group">
    <a href="https://dustanddynasty.gumroad.com/l/coffee" class="sidebar-btn sidebar-btn-one-time" target="_blank" rel="noopener">☕ Buy Me a Coffee</a>
    <a href="https://www.patreon.com/cw/dustanddynasty" class="sidebar-btn sidebar-btn-monthly" target="_blank" rel="noopener">🔁 Monthly Support</a>
  </div>
</div>
'''.strip()

def fetch_all_posts(service, blog_id, status):
    """Fetch all posts with given status (LIVE or DRAFT)."""
    posts = []
    page_token = None
    while True:
        res = service.posts().list(blogId=blog_id, status=status, maxResults=100, pageToken=page_token).execute()
        posts.extend(res.get('items', []))
        page_token = res.get('nextPageToken')
        if not page_token:
            break
    return posts

def has_new_banner(soup):
    """Check if post already has the new banner (idempotency guard)."""
    return soup.find(class_='post-support-banner') is not None

def remove_legacy_banners(soup):
    """Remove legacy banners by class only (no text matching)."""
    removed = 0
    for div in soup.find_all('div', class_='sidebar-support-banner'):
        div.decompose()
        removed += 1
    return removed

def inject_new_banner(soup):
    """Append new banner to the end of the content."""
    # Blogger content is a fragment; append to root soup
    soup.append(BeautifulSoup(NEW_BANNER_HTML, 'html.parser'))

def process_post(service, blog_id, post):
    """Process a single post: remove legacy banners, inject new banner if missing."""
    post_id = post['id']
    title = post.get('title', '')[:60]
    
    # Get full content
    full = service.posts().get(blogId=blog_id, postId=post_id, view="AUTHOR", fetchBody=True).execute()
    content = full.get('content', '')
    search_description = full.get('searchDescription', '')
    labels = full.get('labels', [])
    
    if not content:
        print(f"  [SKIP] {title} - no content")
        return False, 0
    
    soup = BeautifulSoup(content, 'html.parser')
    
    # IDEMPOTENCY: Skip if new banner already present
    if has_new_banner(soup):
        print(f"  [SKIP] {title} - new banner already present")
        return False, 0
    
    # Check and remove legacy banners (class-based only)
    removed = remove_legacy_banners(soup)
    
    # Inject new banner
    inject_new_banner(soup)
    
    # Update post
    new_content = str(soup)
    if new_content != content or removed > 0:
        body = {
            'id': post_id,
            'title': full.get('title'),
            'content': new_content,
            'searchDescription': search_description,
            'labels': labels
        }
        try:
            service.posts().patch(blogId=blog_id, postId=post_id, body=body).execute()
            print(f"  [UPDATED] {title} (removed {removed} legacy banner(s))")
            return True, removed
        except Exception as e:
            print(f"  [ERROR] {title}: {e}")
            return False, removed
    else:
        print(f"  [UNCHANGED] {title}")
        return False, 0

def main():
    print("=== Banner Replacement Script (Fixed) ===")
    print("Fetching Blogger service...")
    
    service = get_blogger_service()
    blog = service.blogs().getByUrl(url='https://dustanddynasty.blogspot.com').execute()
    blog_id = blog['id']
    
    print(f"Blog ID: {blog_id}")
    
    # Fetch LIVE posts
    print("\n--- Fetching LIVE posts ---")
    live_posts = fetch_all_posts(service, blog_id, 'LIVE')
    print(f"Found {len(live_posts)} LIVE posts")
    
    # Fetch DRAFT posts
    print("\n--- Fetching DRAFT posts ---")
    draft_posts = fetch_all_posts(service, blog_id, 'DRAFT')
    print(f"Found {len(draft_posts)} DRAFT posts")
    
    all_posts = live_posts + draft_posts
    print(f"\nTotal posts to process: {len(all_posts)}")
    
    updated_count = 0
    total_removed = 0
    
    for i, post in enumerate(all_posts, 1):
        print(f"\n[{i}/{len(all_posts)}] Processing: {post.get('title', '')[:60]}")
        updated, removed = process_post(service, blog_id, post)
        if updated:
            updated_count += 1
        total_removed += removed
        
        # RATE LIMITING: 1 second between patches
        if i < len(all_posts):
            time.sleep(1.0)
    
    print(f"\n=== SUMMARY ===")
    print(f"Posts updated: {updated_count}")
    print(f"Legacy banners removed: {total_removed}")
    print(f"New banners injected: {updated_count}")

if __name__ == "__main__":
    main()