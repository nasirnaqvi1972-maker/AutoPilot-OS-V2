#!/usr/bin/env python3
"""
fix_headings.py

Safely repairs heading hierarchy in Blogger post HTML snapshots.
Rules applied:
1. Multiple <h1> tags: The first <h1> is preserved; any subsequent <h1> tags are converted to <h2>.
2. Hierarchy-breaking <h3> tags: Any <h3> tag that breaks hierarchy (such as appearing immediately
   after an <h1> without an intervening <h2>, or being the first heading in the body) is converted to <h2>.

Features:
- Dry-run mode by default (--dry-run) to preview changes without modifying files.
- Automated timestamped backup creation before in-place modification (--in-place).
- Atomic file writes to eliminate the risk of file corruption.
- Optional --post-id flag to inspect or fix a specific post.
"""

import os
import sys
import json
import shutil
import argparse
import tempfile
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
DEFAULT_SNAPSHOT = ROOT / "content" / "image_audit_20261020" / "audit_v2_posts_snapshot.json"


def normalize_text(text: str) -> str:
    """Strip and collapse whitespace."""
    if not text:
        return ""
    return " ".join(text.split()).strip()


def repair_headings(soup: BeautifulSoup) -> tuple[int, list]:
    """
    Analyzes heading tags in document order.
    Converts redundant <h1> tags (after the first) to <h2>.
    Converts hierarchy-breaking <h3> tags (after <h1> or at start) to <h2>.
    Returns (num_changes, list_of_descriptions).
    """
    headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    changes = []
    prev_level = None
    h1_seen = False

    for h in headings:
        tag_name = h.name.lower()
        h_text = normalize_text(h.get_text())[:45]

        # Rule 1: Convert extra <h1> tags to <h2>
        if tag_name == "h1":
            if h1_seen:
                h.name = "h2"
                tag_name = "h2"
                changes.append(f"Extra <h1> -> converted to <h2>: \"{h_text}\"")
            else:
                h1_seen = True

        # Rule 2: Convert hierarchy-breaking <h3> tags to <h2>
        if tag_name == "h3":
            if prev_level is None:
                # First heading in post body is <h3>
                h.name = "h2"
                tag_name = "h2"
                changes.append(f"First heading <h3> (prev=None) -> converted to <h2>: \"{h_text}\"")
            elif prev_level == 1:
                # <h3> immediately following <h1>
                h.name = "h2"
                tag_name = "h2"
                changes.append(f"Skipped level <h3> (prev=<h1>) -> converted to <h2>: \"{h_text}\"")

        # Update previous heading level
        prev_level = int(tag_name[1])

    return len(changes), changes


def atomic_json_dump(data, file_path: Path) -> None:
    """Safely write JSON to a file using an atomic replace operation."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=file_path.parent, delete=False, encoding="utf-8") as tf:
            temp_file = Path(tf.name)
            json.dump(data, tf, ensure_ascii=False, indent=2)
        temp_file.replace(file_path)
    except Exception:
        if temp_file and temp_file.exists():
            try:
                temp_file.unlink()
            except OSError:
                pass
        raise


def create_backup(file_path: Path) -> Path:
    """Create a timestamped backup copy of a file before modification."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = file_path.with_name(f"{file_path.stem}.bak_{timestamp}{file_path.suffix}")
    shutil.copy2(file_path, backup_path)
    return backup_path


def main():
    parser = argparse.ArgumentParser(description="Repair heading hierarchy in post snapshots.")
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=DEFAULT_SNAPSHOT,
        help="Path to snapshot JSON (default: content/image_audit_20261020/audit_v2_posts_snapshot.json).",
    )
    parser.add_argument(
        "--post-id",
        type=str,
        default=None,
        help="Optional post ID to target a single post.",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Modify the snapshot JSON file in-place (creates a timestamped backup).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional directory to write repaired snapshot without touching original.",
    )

    args = parser.parse_args()

    snap_path = args.snapshot if args.snapshot.is_absolute() else ROOT / args.snapshot
    if not snap_path.exists():
        print(f"[ERROR] Snapshot file not found: {snap_path}", file=sys.stderr)
        sys.exit(1)

    print(f"[INIT] Loading snapshot: {snap_path}")
    with open(snap_path, "r", encoding="utf-8") as f:
        posts = json.load(f)

    # Filter to specific post if --post-id provided
    target_posts = posts
    if args.post_id:
        target_posts = [p for p in posts if str(p.get("id")) == args.post_id]
        if not target_posts:
            print(f"[ERROR] Post ID {args.post_id} not found in {snap_path}", file=sys.stderr)
            sys.exit(1)
        print(f"[FILTER] Targeting single post: {target_posts[0].get('title')} (ID: {args.post_id})")

    dry_run = not args.in_place and args.output_dir is None
    if dry_run:
        print("[MODE] Running in DRY-RUN mode. No files will be modified. Pass --in-place to apply changes.\n")
    elif args.in_place:
        print("[MODE] IN-PLACE mode active. A timestamped backup will be created.\n")
    else:
        print(f"[MODE] Output directed to: {args.output_dir}\n")

    total_posts_modified = 0
    total_headings_modified = 0
    post_changes = []

    for p in target_posts:
        pid = str(p.get("id", ""))
        title = p.get("title", "Untitled")
        content = p.get("content", "")
        if not content:
            continue

        soup = BeautifulSoup(content, "html.parser")
        mod_count, changes = repair_headings(soup)

        if mod_count > 0:
            total_posts_modified += 1
            total_headings_modified += mod_count
            p["content"] = str(soup)
            post_changes.append({
                "id": pid,
                "title": title,
                "count": mod_count,
                "changes": changes,
            })

    # Summary Display
    print("================ HEADING REPAIR SUMMARY ================")
    print(f"Total Posts Scanned:        {len(target_posts)}")
    print(f"Posts Requiring Fixes:      {total_posts_modified}")
    print(f"Headings Converted to <h2>: {total_headings_modified}")
    print("========================================================\n")

    if post_changes:
        print("Sample of Repaired Posts:")
        for change in post_changes[:8]:
            print(f"- [{change['id']}] {change['title']}")
            for c in change["changes"]:
                print(f"    * {c}")
        if len(post_changes) > 8:
            print(f"\n... and {len(post_changes) - 8} more posts repaired.")
        print()

    if dry_run:
        print("[DRY-RUN COMPLETE] To apply these changes, run with --in-place:")
        print(f"  python {Path(__file__).name} --in-place\n")
        return

    # Write output
    if args.in_place:
        backup_file = create_backup(snap_path)
        print(f"[BACKUP] Created snapshot backup at: {backup_file}")
        atomic_json_dump(posts, snap_path)
        print(f"[SAVED] Updated snapshot written to: {snap_path}")
    elif args.output_dir:
        out_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        out_snap = out_dir / snap_path.name
        atomic_json_dump(posts, out_snap)
        print(f"[SAVED] Repaired snapshot written to: {out_snap}")

    print("\n[SUCCESS] Heading hierarchy repairs successfully completed.")


if __name__ == "__main__":
    main()
