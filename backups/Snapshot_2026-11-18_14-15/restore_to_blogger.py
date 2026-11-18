#!/usr/bin/env python3
"""
restore_to_blogger.py - UPDATED

Surgically patches existing Blogger post content AND title via the Blogger API.
Matches snapshot posts to Blogger posts by URL using verified_inventory.json.
"""

import sys
import json
import time
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core.blogger_publisher import get_blogger_service

BLOG_URL = "https://dustanddynasty.blogspot.com"
DEFAULT_SNAPSHOT = ROOT / "content" / "image_audit_20261020" / "audit_v2_posts_snapshot.json"
INVENTORY = ROOT / "verified_inventory.json"
RATE_LIMIT_DELAY = 2


def build_url_to_blogger_id():
    """Load verified_inventory.json and return {url: blogger_post_id} mapping."""
    with open(INVENTORY, 'r', encoding='utf-8') as f:
        inv = json.load(f)
    mapping = {}
    for blogger_id, meta in inv.get('posts', {}).items():
        url = meta.get('url', '').rstrip('/')
        if url:
            mapping[url] = blogger_id
    return mapping


def patch_single_post(service, blog_id: str, post_id: str, html_content: str, post_title: str = "", dry_run: bool = False) -> bool:
    """Sends a patch request to Blogger API to update post content and title."""
    print(f"\n[PATCH] Target Blogger Post ID: {post_id}")
    if post_title:
        print(f"[PATCH] Title: {post_title}")
    print(f"[PATCH] Content Size: {len(html_content)} characters ({len(html_content.encode('utf-8'))} bytes)")

    if dry_run:
        print("[DRY-RUN] Simulating API call. No changes were sent to Blogger.")
        return True

    body = {"content": html_content}
    if post_title:
        body["title"] = post_title

    try:
        print(f"[API] Patching post on Blogger...")
        result = service.posts().patch(blogId=blog_id, postId=post_id, body=body).execute()
        print("\n[SUCCESS] Post successfully updated on live site!")
        print(f"[SUCCESS] Title: {result.get('title')}")
        print(f"[SUCCESS] URL:   {result.get('url')}")
        print(f"[SUCCESS] Updated: {result.get('updated')}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to patch post {post_id}: {e}", file=sys.stderr)
        return False


def patch_all_posts(service, blog_id: str, posts: list, url_to_bid: dict, dry_run: bool = False) -> None:
    """Iterates through all posts in the snapshot and patches them by matched Blogger ID."""
    total = len(posts)
    success_count = 0
    failure_count = 0
    skipped_count = 0

    mode_label = "[DRY-RUN] " if dry_run else ""
    print(f"\n{mode_label}Starting batch patch for {total} posts...")
    if not dry_run:
        print(f"Applying rate limit delay of {RATE_LIMIT_DELAY}s between API calls.\n")

    for idx, p in enumerate(posts, 1):
        snap_id = str(p.get("id", ""))
        title = p.get("title", "Untitled")
        content = p.get("content", "")
        snap_url = p.get("url", "").rstrip('/')

        blogger_id = url_to_bid.get(snap_url)
        
        print(f"Patching {idx}/{total}: [{title}] (Snapshot ID: {snap_id})")

        if not blogger_id:
            print(f"  [SKIP] No matching Blogger post for URL: {snap_url}")
            skipped_count += 1
            continue
        if not content:
            print(f"  [SKIP] Empty content.")
            skipped_count += 1
            continue

        if dry_run:
            print(f"  [DRY-RUN] Would patch Blogger ID {blogger_id} ({len(content)} chars). Title: {title[:60]}")
            success_count += 1
        else:
            body = {"content": content}
            if title and title != "Untitled":
                body["title"] = title
            try:
                result = service.posts().patch(blogId=blog_id, postId=blogger_id, body=body).execute()
                print(f"  [OK] Successfully patched Blogger ID {blogger_id}: {result.get('url')}")
                success_count += 1
            except Exception as e:
                print(f"  [ERROR] Failed to patch Blogger ID {blogger_id}: {e}", file=sys.stderr)
                failure_count += 1

            if idx < total:
                time.sleep(RATE_LIMIT_DELAY)

    print("\n================ BATCH SUMMARY ================")
    print(f"  Total Posts:     {total}")
    print(f"  Successful:      {success_count}")
    print(f"  Failed:          {failure_count}")
    print(f"  Skipped:         {skipped_count}")
    print("===============================================\n")


def main():
    parser = argparse.ArgumentParser(description="Surgically patch Blogger post content and title.")
    parser.add_argument("--post-id", type=str, default=None, help="Specific Blogger Post ID to patch (requires --url).")
    parser.add_argument("--url", type=str, default=None, help="URL of the post (for matching with inventory).")
    parser.add_argument("--all", action="store_true", help="Patch all posts in snapshot matched by URL.")
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT, help="Path to snapshot JSON.")
    parser.add_argument("--html-file", type=Path, default=None, help="HTML file to patch a single post.")
    parser.add_argument("--dry-run", action="store_true", help="Preview without modifying live posts.")
    args = parser.parse_args()

    # Load URL -> Blogger ID mapping
    url_to_bid = build_url_to_blogger_id()
    print(f"[LOAD] Loaded {len(url_to_bid)} URL -> Blogger ID mappings from verified_inventory.json")

    # Authenticate
    service = None
    blog_id = None
    if not args.dry_run:
        print("[API] Authenticating with Blogger API...")
        try:
            service = get_blogger_service()
            blog = service.blogs().getByUrl(url=BLOG_URL).execute()
            blog_id = blog["id"]
            print(f"[API] Connected to blog: {blog.get('name')} (ID: {blog_id})")
        except Exception as e:
            print(f"[ERROR] Failed to authenticate: {e}", file=sys.stderr)
            sys.exit(1)

    # Mode 1: Batch patch ALL posts
    if args.all:
        snap_path = args.snapshot if args.snapshot.is_absolute() else ROOT / args.snapshot
        if not snap_path.exists():
            print(f"[ERROR] Snapshot not found: {snap_path}", file=sys.stderr)
            sys.exit(1)
        print(f"[LOAD] Loading posts from snapshot: {snap_path}")
        with open(snap_path, "r", encoding="utf-8") as f:
            posts = json.load(f)
        patch_all_posts(service, blog_id, posts, url_to_bid, dry_run=args.dry_run)
        return

    # Mode 2: Single post from HTML file
    if args.html_file:
        if not args.post_id or not args.url:
            print("[ERROR] --post-id and --url required with --html-file.", file=sys.stderr)
            sys.exit(1)
        html_path = args.html_file if args.html_file.is_absolute() else ROOT / args.html_file
        if not html_path.exists():
            print(f"[ERROR] HTML file not found: {html_path}", file=sys.stderr)
            sys.exit(1)
        html_content = html_path.read_text(encoding="utf-8")
        title = html_path.stem
        blogger_id = url_to_bid.get(args.url.rstrip('/'))
        if not blogger_id:
            print(f"[ERROR] No Blogger ID for URL: {args.url}", file=sys.stderr)
            sys.exit(1)
        ok = patch_single_post(service, blog_id, blogger_id, html_content, post_title=title, dry_run=args.dry_run)
        if not ok:
            sys.exit(1)
        return

    # Mode 3: Single post from snapshot by URL
    if args.url:
        snap_path = args.snapshot if args.snapshot.is_absolute() else ROOT / args.snapshot
        if not snap_path.exists():
            print(f"[ERROR] Snapshot not found: {snap_path}", file=sys.stderr)
            sys.exit(1)
        with open(snap_path, "r", encoding="utf-8") as f:
            posts = json.load(f)
        target_url = args.url.rstrip('/')
        target_post = next((p for p in posts if p.get("url", "").rstrip('/') == target_url), None)
        if not target_post:
            print(f"[ERROR] URL not found in snapshot: {target_url}", file=sys.stderr)
            sys.exit(1)
        blogger_id = url_to_bid.get(target_url)
        if not blogger_id:
            print(f"[ERROR] No Blogger ID for URL: {target_url}", file=sys.stderr)
            sys.exit(1)
        html_content = target_post.get("content", "")
        title = target_post.get("title", "")
        if not html_content:
            print(f"[ERROR] Empty content for URL: {target_url}", file=sys.stderr)
            sys.exit(1)
        ok = patch_single_post(service, blog_id, blogger_id, html_content, post_title=title, dry_run=args.dry_run)
        if not ok:
            sys.exit(1)
        return

    # Default: show help
    parser.print_help()


if __name__ == "__main__":
    main()
