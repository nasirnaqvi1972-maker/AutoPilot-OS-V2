#!/usr/bin/env python3
"""
pull_specific_drafts.py - Pull specific Blogger drafts back into content/pending/
for re-processing with the fixed pipeline code.

Phase 1: THE ELEPHANT (Implementation)
- Fetch drafts matching target titles
- Strip <img>, <iframe>, <figure> tags (force fresh image fetching)
- Save to content/pending/<slug>.html
- DELETE the draft from Blogger to prevent duplicates
"""

import os
import re
import sys
import unicodedata
from pathlib import Path

# Add project root to path so we can import from core/
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core.blogger_publisher import get_blogger_service, execute_with_retry
from bs4 import BeautifulSoup

PENDING_DIR = ROOT / "content" / "pending"

# Target titles to match (partial match - contains these strings)
TARGET_PATTERNS = [
    "Ichkeul National Park",
    "City of Quito",
    "Gal\u00e1pagos Islands",
]

BANNER_START = "<!--Start of Dust and Dynasty Sidebar Support Banner-->"
BANNER_END = "<!--End of Dust and Dynasty Sidebar Support Banner-->"


def slugify(title):
    """Create URL/filesystem-safe slug from title."""
    text = unicodedata.normalize("NFKD", title)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    text = re.sub(r"-{2,}", "-", text)
    return text[:120] or "draft"


def strip_support_banner(html: str) -> str:
    """Remove any existing Dust and Dynasty support banner blocks from HTML."""
    if BANNER_START not in html or BANNER_END not in html:
        return html
    start_idx = html.find(BANNER_START)
    end_idx = html.find(BANNER_END)
    if start_idx == -1 or end_idx == -1:
        return html
    end_idx += len(BANNER_END)
    cleaned = html[:start_idx] + html[end_idx:]
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def clean_html_for_reprocessing(html: str) -> str:
    """
    Strip <img>, <iframe>, and <figure> tags so the engine fetches fresh images.
    Also strips the support banner.
    """
    # First strip the support banner
    html = strip_support_banner(html)
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Remove all <img> tags
    for img in soup.find_all('img'):
        img.decompose()
    
    # Remove all <iframe> tags
    for iframe in soup.find_all('iframe'):
        iframe.decompose()
    
    # Remove all <figure> tags (and their contents)
    for figure in soup.find_all('figure'):
        figure.decompose()
    
    # Also remove empty anchor tags that might have wrapped images
    for a in soup.find_all('a'):
        if not a.get_text(strip=True) and not a.find('img'):
            a.decompose()
    
    return str(soup)


def main():
    PENDING_DIR.mkdir(parents=True, exist_ok=True)

    print("[pull_specific_drafts] Connecting to Blogger API...")
    service = get_blogger_service()

    blog = execute_with_retry(service.blogs().getByUrl(url='https://dustanddynasty.blogspot.com'))
    blog_id = blog['id']
    print(f"[pull_specific_drafts] Blog ID: {blog_id}")

    # List all drafts
    print("[pull_specific_drafts] Listing draft posts...")
    found = {}  # title -> {id, content}
    page_token = None
    total_drafts = 0
    
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
        items = res.get('items', [])
        total_drafts += len(items)
        
        for item in items:
            title = item.get('title', '')
            # Check if title matches any of our target patterns (partial match)
            for pattern in TARGET_PATTERNS:
                if pattern in title:
                    # Use full title as key to handle duplicates (e.g., two "City of Quito" drafts)
                    if title not in found:
                        found[title] = {
                            'id': item['id'],
                            'content': item.get('content', ''),
                        }
                        print(f"  [pull_specific_drafts] Found draft: '{title}' (ID: {item['id']})")
                    else:
                        print(f"  [pull_specific_drafts] DUPLICATE title found: '{title}' (ID: {item['id']}) - will process both")
        
        page_token = res.get('nextPageToken')
        if not page_token:
            break
    
    print(f"[pull_specific_drafts] Total drafts scanned: {total_drafts}")
    print(f"[pull_specific_drafts] Matching drafts found: {len(found)}")

    if not found:
        print("[pull_specific_drafts] No matching drafts found. Exiting.")
        return

    # Process each found draft
    processed_count = 0
    deleted_count = 0
    errors = []
    
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
                err = f"ERROR fetching '{title}': {e}"
                print(f"  [pull_specific_drafts] {err}")
                errors.append(err)
                continue
        
        if not html_content:
            err = f"No content for '{title}', skipping."
            print(f"  [pull_specific_drafts] {err}")
            errors.append(err)
            continue

        # Clean HTML: strip images, iframes, figures, and support banner
        cleaned = clean_html_for_reprocessing(html_content)
        
        # Save to pending
        slug = slugify(title)
        output_path = PENDING_DIR / f"{slug}.html"
        
        # Ensure we handle BOM
        cleaned = cleaned.replace('\ufeff', '')
        
        output_path.write_text(cleaned, encoding='utf-8')
        print(f"  [PULL] Saved '{title}' to {output_path} ({len(cleaned)} chars)")
        processed_count += 1

        # CRITICAL: Delete the draft from Blogger to prevent duplicates
        print(f"  [pull_specific_drafts] Deleting draft from Blogger (ID: {post_id})...")
        try:
            delete_req = service.posts().delete(blogId=blog_id, postId=post_id)
            execute_with_retry(delete_req)
            print(f"  [pull_specific_drafts] DELETED draft from Blogger.")
            deleted_count += 1
        except Exception as e:
            err = f"FAILED to delete draft '{title}' (ID: {post_id}): {e}"
            print(f"  [pull_specific_drafts] {err}")
            errors.append(err)
            # Continue processing other drafts even if one delete fails

    print(f"\n{'='*60}")
    print(f"[pull_specific_drafts] SUMMARY:")
    print(f"  Total matching drafts found: {len(found)}")
    print(f"  Successfully saved to pending: {processed_count}")
    print(f"  Successfully deleted from Blogger: {deleted_count}")
    if errors:
        print(f"  Errors encountered: {len(errors)}")
        for err in errors:
            print(f"    - {err}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()