#!/usr/bin/env python3
"""
pull_specific_drafts.py - Pull specific Blogger drafts back into content/pending/
for re-processing with the fixed pipeline code.
"""

import os
import re
import sys
from pathlib import Path

# Add project root to path so we can import from core/
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core.blogger_publisher import get_blogger_service, execute_with_retry
from ai_draft_generator import slugify

PENDING_DIR = ROOT / "content" / "pending"
TARGET_TITLES = [
    "City of Quito: The Preserved Colonial Jewel of the Andes",
    "Gal\u00e1pagos Islands",
]

BANNER_START = "<!--Start of Dust and Dynasty Sidebar Support Banner-->"
BANNER_END = "<!--End of Dust and Dynasty Sidebar Support Banner-->"


def strip_support_banner(html: str) -> str:
    """Remove any existing Dust and Dynasty support banner blocks from HTML."""
    if BANNER_START not in html or BANNER_END not in html:
        return html
    start_idx = html.find(BANNER_START)
    end_idx = html.find(BANNER_END)
    if start_idx == -1 or end_idx == -1:
        return html
    # Remove from start of BANNER_START to end of BANNER_END tag
    end_idx += len(BANNER_END)
    # Also strip trailing whitespace/newlines left behind
    cleaned = html[:start_idx] + html[end_idx:]
    # Collapse multiple blank lines that may remain
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def main():
    PENDING_DIR.mkdir(parents=True, exist_ok=True)

    print("[pull_specific_drafts] Connecting to Blogger API...")
    service = get_blogger_service()

    blog = execute_with_retry(service.blogs().getByUrl(url='https://dustanddynasty.blogspot.com'))
    blog_id = blog['id']
    print(f"[pull_specific_drafts] Blog ID: {blog_id}")

    # List all drafts
    print("[pull_specific_drafts] Listing draft posts...")
    found = {}
    page_token = None
    while True:
        list_req = service.posts().list(
            blogId=blog_id,
            status=['DRAFT'],
            maxResults=100,
            pageToken=page_token,
            view='ADMIN',
            fetchBodies=True,
        )
        res = execute_with_retry(list_req)
        for item in res.get('items', []):
            title = item.get('title', '')
            if title in TARGET_TITLES and title not in found:
                found[title] = {
                    'id': item['id'],
                    'content': item.get('content', ''),
                }
                print(f"  [pull_specific_drafts] Found draft: '{title}' (ID: {item['id']})")
        if len(found) == len(TARGET_TITLES):
            break
        page_token = res.get('nextPageToken')
        if not page_token:
            break

    missing = [t for t in TARGET_TITLES if t not in found]
    if missing:
        print(f"[pull_specific_drafts] WARNING: Could not find drafts: {missing}")

    # Process each found draft (content already fetched via fetchBodies=True)
    for title, data in found.items():
        post_id = data['id']
        print(f"\n[pull_specific_drafts] Processing: '{title}' (ID: {post_id})...")
        html_content = data.get('content', '')
        if not html_content:
            print(f"  [pull_specific_drafts] No content in list response, trying posts().get()...")
            try:
                post = execute_with_retry(
                    service.posts().get(blogId=blog_id, postId=post_id, view='ADMIN')
                )
                html_content = post.get('content', '')
            except Exception as e:
                print(f"  [pull_specific_drafts] ERROR fetching '{title}': {e}")
                continue
        if not html_content:
            print(f"  [pull_specific_drafts] No content for '{title}', skipping.")
            continue

        # Strip any existing support banner
        cleaned = strip_support_banner(html_content)

        # Save to pending
        slug = slugify(title)
        output_path = PENDING_DIR / f"{slug}.html"
        output_path.write_text(cleaned, encoding='utf-8')
        print(f"  [pull_specific_drafts] Saved: {output_path} ({len(cleaned)} chars)")

    print(f"\n[pull_specific_drafts] Done. {len(found)} of {len(TARGET_TITLES)} drafts pulled.")


if __name__ == "__main__":
    main()
