# -*- coding: utf-8 -*-
"""
audit_duplicate_images.py — Live Blogger Duplicate Image Auditor
================================================================
Read-only audit tool for AutoPilot OS V2.
Connects to the Blogger API, fetches all posts (LIVE & DRAFT),
extracts hosted image URLs from post HTML, and identifies duplicate
images shared across multiple posts.

Author: Antigravity (EGM Elephant Mode)
"""

import os
import sys
import io
import json
import time
import datetime
from pathlib import Path
from collections import defaultdict
from bs4 import BeautifulSoup

# Ensure UTF-8 stdout on Windows console
if sys.stdout and sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass

# Ensure project root is in sys.path
V2_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(V2_ROOT))

from core.blogger_publisher import get_blogger_service, execute_with_retry

BLOG_URL = "https://dustanddynasty.blogspot.com"
REPORTS_DIR = V2_ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# System/tracking images to ignore during duplicate analysis
IGNORED_PATTERNS = [
    "resources.blogblog.com",
    "b.scorecardresearch.com",
    "blogger.googleusercontent.com/tracker",
    "data:image/svg+xml",
    "data:image/gif",
    "1x1",
]


def safe_print(msg: str):
    """Print safely to console on Windows."""
    try:
        print(msg)
    except UnicodeEncodeError:
        safe = msg.encode("cp1252", errors="replace").decode("cp1252")
        print(safe)


def is_trackable_image(src: str) -> bool:
    """Returns True if the image URL is a real content asset, not tracking or empty."""
    if not src or not src.strip():
        return False
    src_lower = src.strip().lower()
    for pattern in IGNORED_PATTERNS:
        if pattern in src_lower:
            return False
    return True


def normalize_image_url(src: str) -> str:
    """Normalizes image URL by stripping surrounding whitespace and fragment identifiers."""
    url = src.strip()
    if "#" in url:
        url = url.split("#", 1)[0]
    return url


def fetch_all_posts(service, blog_id):
    """
    Fetches all posts (both LIVE and DRAFT) with pagination using Blogger API v3.
    Returns a dict mapping post_id -> post dict.
    """
    posts_by_id = {}
    statuses = ["LIVE", "DRAFT"]

    for status in statuses:
        safe_print(f"[*] Fetching {status} posts from Blogger...")
        page_token = None
        count = 0

        while True:
            req = service.posts().list(
                blogId=blog_id,
                status=status,
                maxResults=100,
                pageToken=page_token,
                fetchBodies=True
            )
            res = execute_with_retry(req)
            items = res.get("items", [])

            for item in items:
                pid = item["id"]
                if pid not in posts_by_id:
                    posts_by_id[pid] = item
                    count += 1

            page_token = res.get("nextPageToken")
            if not page_token:
                break
            time.sleep(0.15)  # Pacing pause to respect rate limits

        safe_print(f"    -> Retreived {count} {status} posts.")

    safe_print(f"[OK] Total unique posts retrieved: {len(posts_by_id)}\n")
    return posts_by_id


def extract_post_images(posts_by_id):
    """
    Parses HTML content for each post and builds index mappings.
    Returns:
      image_to_posts: dict of image_url -> list of post info dicts
      post_to_images: dict of post_id -> list of image_urls
    """
    image_to_posts = defaultdict(list)
    post_to_images = defaultdict(list)

    for pid, post in posts_by_id.items():
        title = post.get("title", "Untitled").strip()
        status = post.get("status", "UNKNOWN")
        url = post.get("url", "")
        content = post.get("content", "")

        if not content:
            continue

        soup = BeautifulSoup(content, "html.parser")
        seen_in_this_post = set()

        for img in soup.find_all("img"):
            src = img.get("src")
            if not is_trackable_image(src):
                continue

            clean_url = normalize_image_url(src)
            alt = img.get("alt", "").strip()

            post_info = {
                "post_id": pid,
                "title": title,
                "status": status,
                "url": url,
                "alt": alt
            }

            # Avoid adding the exact same post multiple times for one image URL in image_to_posts
            if clean_url not in seen_in_this_post:
                image_to_posts[clean_url].append(post_info)
                seen_in_this_post.add(clean_url)

            post_to_images[pid].append(clean_url)

    return image_to_posts, post_to_images


def run_audit():
    """Runs the full duplicate image audit pipeline."""
    start_time = datetime.datetime.now()
    safe_print("=" * 70)
    safe_print(f"  DUST & DYNASTY — BLOGGER DUPLICATE IMAGE AUDITOR")
    safe_print(f"  Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    safe_print("=" * 70)

    # 1. Connect & Authenticate
    safe_print("[*] Connecting to Google Blogger API...")
    service = get_blogger_service()
    blog_req = service.blogs().getByUrl(url=BLOG_URL)
    blog = execute_with_retry(blog_req)
    blog_id = blog["id"]
    safe_print(f"[OK] Connected to Blog: {blog.get('name')} (ID: {blog_id})")

    # 2. Fetch all posts
    posts_by_id = fetch_all_posts(service, blog_id)

    # 3. Extract and map images
    safe_print("[*] Parsing HTML content and indexing image URLs...")
    image_to_posts, post_to_images = extract_post_images(posts_by_id)

    # 4. Identify duplicates (shared across 2 or more distinct posts)
    cross_post_duplicates = {
        img_url: posts
        for img_url, posts in image_to_posts.items()
        if len(posts) > 1
    }

    # Identify posts with internal duplicate images (same image repeated inside single post)
    intra_post_repeats = defaultdict(list)
    for pid, img_list in post_to_images.items():
        counts = defaultdict(int)
        for u in img_list:
            counts[u] += 1
        for u, c in counts.items():
            if c > 1:
                intra_post_repeats[pid].append((u, c))

    # 5. Output Report
    total_images_referenced = sum(len(imgs) for imgs in post_to_images.values())
    total_unique_images = len(image_to_posts)
    total_duplicate_urls = len(cross_post_duplicates)

    report_lines = []
    def log_and_collect(line=""):
        safe_print(line)
        report_lines.append(line)

    log_and_collect("\n" + "=" * 70)
    log_and_collect("  AUDIT SUMMARY")
    log_and_collect("=" * 70)
    log_and_collect(f"Total Posts Scanned         : {len(posts_by_id)}")
    log_and_collect(f"Total Image Tags Extracted   : {total_images_referenced}")
    log_and_collect(f"Total Unique Image URLs      : {total_unique_images}")
    log_and_collect(f"Cross-Post Duplicate URLs    : {total_duplicate_urls}")
    log_and_collect(f"Posts with Intra-Repeats     : {len(intra_post_repeats)}")
    log_and_collect("=" * 70 + "\n")

    if not cross_post_duplicates:
        log_and_collect("[+] SUCCESS: Zero duplicate images found across live and draft posts!")
    else:
        log_and_collect(f"[!] DETECTED {total_duplicate_urls} DUPLICATE IMAGE(S) SHARED ACROSS POSTS:\n")
        
        # Sort by frequency (most duplicated first)
        sorted_dupes = sorted(cross_post_duplicates.items(), key=lambda x: len(x[1]), reverse=True)

        for idx, (img_url, post_list) in enumerate(sorted_dupes, 1):
            log_and_collect(f"----------------------------------------------------------------------")
            log_and_collect(f"Duplicate #{idx} (Shared across {len(post_list)} posts)")
            log_and_collect(f"URL: {img_url}")
            log_and_collect(f"Appears in:")
            for p in post_list:
                log_and_collect(f"  - [{p['status']}] {p['title']}")
                log_and_collect(f"    Post ID : {p['post_id']}")
                if p["url"]:
                    log_and_collect(f"    Live URL: {p['url']}")
                if p["alt"]:
                    log_and_collect(f"    Alt Text: \"{p['alt']}\"")

    if intra_post_repeats:
        log_and_collect("\n" + "-" * 70)
        log_and_collect("  INTRA-POST REPETITIONS (Same image repeated within 1 post):")
        log_and_collect("-" * 70)
        for pid, repeat_list in intra_post_repeats.items():
            post_title = posts_by_id[pid].get("title", "Untitled")
            log_and_collect(f"• Post: {post_title} (ID: {pid})")
            for url, count in repeat_list:
                log_and_collect(f"    - Repeated {count}x: {url}")

    # 6. Save Reports to Disk
    ts_str = start_time.strftime("%Y%m%d_%H%M%S")
    txt_report_file = REPORTS_DIR / f"duplicate_images_audit_{ts_str}.txt"
    latest_txt_file = REPORTS_DIR / "duplicate_images_audit_latest.txt"
    json_report_file = REPORTS_DIR / "duplicate_images_audit.json"

    with open(txt_report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")

    with open(latest_txt_file, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")

    json_payload = {
        "timestamp": start_time.isoformat(),
        "summary": {
            "total_posts": len(posts_by_id),
            "total_image_tags": total_images_referenced,
            "total_unique_images": total_unique_images,
            "cross_post_duplicate_urls": total_duplicate_urls,
            "posts_with_intra_repeats": len(intra_post_repeats)
        },
        "duplicates": [
            {
                "image_url": url,
                "shared_count": len(plist),
                "posts": plist
            }
            for url, plist in sorted_dupes
        ] if cross_post_duplicates else []
    }

    with open(json_report_file, "w", encoding="utf-8") as f:
        json.dump(json_payload, f, indent=2, ensure_ascii=False)

    safe_print(f"\n[OK] Reports saved to:")
    safe_print(f"     - {txt_report_file}")
    safe_print(f"     - {latest_txt_file}")
    safe_print(f"     - {json_report_file}")
    safe_print(f"Finished in {(datetime.datetime.now() - start_time).total_seconds():.2f}s.\n")


if __name__ == "__main__":
    run_audit()
