#!/usr/bin/env python3
"""
fix_external_links.py

Safely audits and repairs external links in Blogger post snapshots.
For all outbound links to external domains:
1. Ensures target="_blank" is present.
2. Ensures rel="noopener noreferrer" is injected, preserving any existing rel tokens (e.g., nofollow).

Features:
- Dry-run mode by default (--dry-run) to inspect proposed changes without modifying files.
- Automated timestamped backup creation before in-place modification (--in-place).
- Atomic file writes to prevent snapshot corruption.
- Updates both HTML content (audit_v2_posts_snapshot.json) and parsed link metadata (audit_v2_parsed.json).
"""

import os
import sys
import json
import shutil
import argparse
import tempfile
from pathlib import Path
from datetime import datetime
from urllib.parse import urlsplit
from bs4 import BeautifulSoup

# Internal blog and native platform media CDNs
INTERNAL_DOMAINS = {
    "dustanddynasty.blogspot.com",
    "blogger.com",
    "www.blogger.com",
    "bp.blogspot.com",
    "blogger.googleusercontent.com",
    "googleusercontent.com",
}


def is_external_link(href: str) -> bool:
    """Check if a URL points to an external, third-party domain."""
    if not href:
        return False
    clean_href = href.strip()
    if not clean_href.startswith(("http://", "https://", "//")):
        return False

    parts = urlsplit(clean_href)
    netloc = parts.netloc.lower()
    if not netloc:
        return False

    # Check against internal blog and media domains
    for domain in INTERNAL_DOMAINS:
        if netloc == domain or netloc.endswith("." + domain):
            return False

    return True


def repair_post_links(soup: BeautifulSoup) -> tuple[int, list]:
    """
    Inspects all <a> tags in the post HTML and injects target="_blank"
    and rel="noopener noreferrer" on external links.
    Returns (num_links_modified, list_of_change_descriptions).
    """
    modified_count = 0
    change_log = []

    for a in soup.find_all("a"):
        href = (a.get("href") or "").strip()
        if not is_external_link(href):
            continue

        link_changed = False
        reasons = []

        # 1. Enforce target="_blank"
        current_target = a.get("target")
        if current_target != "_blank":
            a["target"] = "_blank"
            link_changed = True
            reasons.append(f'target="{current_target}" -> target="_blank"')

        # 2. Enforce rel="noopener noreferrer"
        current_rel = a.get("rel")
        if current_rel is None:
            rel_tokens = []
        elif isinstance(current_rel, str):
            rel_tokens = current_rel.split()
        elif isinstance(current_rel, list):
            rel_tokens = list(current_rel)
        else:
            rel_tokens = []

        existing_lower = [t.lower() for t in rel_tokens]
        added_rel = []
        for required_token in ["noopener", "noreferrer"]:
            if required_token not in existing_lower:
                rel_tokens.append(required_token)
                added_rel.append(required_token)
                link_changed = True

        if added_rel:
            a["rel"] = " ".join(rel_tokens)
            reasons.append(f"added rel token(s): {', '.join(added_rel)}")

        if link_changed:
            modified_count += 1
            change_log.append({
                "href": href,
                "reasons": reasons,
            })

    return modified_count, change_log


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
    parser = argparse.ArgumentParser(
        description="Safely inject target='_blank' and rel='noopener noreferrer' into external links."
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=Path("content/image_audit_20261020/audit_v2_posts_snapshot.json"),
        help="Path to audit_v2_posts_snapshot.json (HTML content).",
    )
    parser.add_argument(
        "--parsed",
        type=Path,
        default=Path("content/image_audit_20261020/audit_v2_parsed.json"),
        help="Path to audit_v2_parsed.json (parsed metadata).",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Modify the snapshot and parsed JSON files in-place (creates timestamped backups).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional directory to write repaired files without touching originals.",
    )

    args = parser.parse_args()

    v2_root = Path(__file__).resolve().parent
    snap_path = args.snapshot if args.snapshot.is_absolute() else v2_root / args.snapshot
    parsed_path = args.parsed if args.parsed.is_absolute() else v2_root / args.parsed

    if not snap_path.exists():
        print(f"[ERROR] Snapshot file not found: {snap_path}", file=sys.stderr)
        sys.exit(1)

    print(f"[INIT] Loading snapshot: {snap_path}")
    with open(snap_path, "r", encoding="utf-8") as f:
        posts = json.load(f)

    parsed_posts = None
    if parsed_path.exists():
        print(f"[INIT] Loading parsed metadata: {parsed_path}")
        with open(parsed_path, "r", encoding="utf-8") as f:
            parsed_posts = json.load(f)
        parsed_dict = {p["id"]: p for p in parsed_posts if "id" in p}
    else:
        parsed_dict = {}

    dry_run = not args.in_place and args.output_dir is None
    if dry_run:
        print("[MODE] Running in DRY-RUN mode. No files will be modified. Pass --in-place to apply changes.\n")
    elif args.in_place:
        print("[MODE] IN-PLACE mode active. Backups will be created before saving.\n")
    else:
        print(f"[MODE] Output directed to: {args.output_dir}\n")

    total_posts_modified = 0
    total_links_modified = 0
    post_changes = []

    for p in posts:
        pid = p.get("id")
        title = p.get("title", "Untitled")
        content = p.get("content", "")
        if not content:
            continue

        soup = BeautifulSoup(content, "html.parser")
        modified_count, changes = repair_post_links(soup)

        if modified_count > 0:
            total_posts_modified += 1
            total_links_modified += modified_count
            new_content = str(soup)
            p["content"] = new_content

            # Also update parsed_posts link entries if available
            if pid in parsed_dict:
                parsed_entry = parsed_dict[pid]
                for link in parsed_entry.get("links", []):
                    href = link.get("href", "")
                    if is_external_link(href):
                        link["target_blank"] = True

            post_changes.append({
                "id": pid,
                "title": title,
                "modified_count": modified_count,
                "changes": changes,
            })

    # Display dry-run / execution summary
    print(f"================ SUMMARY ================")
    print(f"Total Posts Scanned:      {len(posts)}")
    print(f"Posts Requiring Fixes:    {total_posts_modified}")
    print(f"External Links Repaired:  {total_links_modified}")
    print(f"=========================================\n")

    if post_changes:
        print("Sample of Repaired Posts:")
        for change in post_changes[:5]:
            print(f"- Post: {change['title']} (ID: {change['id']})")
            print(f"  Fixed {change['modified_count']} external link(s):")
            for c in change["changes"][:3]:
                print(f"    * {c['href']} -> {'; '.join(c['reasons'])}")
            if len(change["changes"]) > 3:
                print(f"    * ... and {len(change['changes']) - 3} more link(s)")
        print()

    if dry_run:
        print("[DRY-RUN COMPLETE] To apply these changes, run with --in-place:")
        print(f"  python {Path(__file__).name} --in-place\n")
        return

    # Write output
    if args.in_place:
        snap_backup = create_backup(snap_path)
        print(f"[BACKUP] Created snapshot backup at: {snap_backup}")
        atomic_json_dump(posts, snap_path)
        print(f"[SAVED] Updated snapshot written to: {snap_path}")

        if parsed_posts is not None:
            parsed_backup = create_backup(parsed_path)
            print(f"[BACKUP] Created parsed metadata backup at: {parsed_backup}")
            atomic_json_dump(parsed_posts, parsed_path)
            print(f"[SAVED] Updated parsed metadata written to: {parsed_path}")
    elif args.output_dir:
        out_dir = args.output_dir if args.output_dir.is_absolute() else v2_root / args.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        out_snap = out_dir / snap_path.name
        atomic_json_dump(posts, out_snap)
        print(f"[SAVED] Modified snapshot written to: {out_snap}")
        if parsed_posts is not None:
            out_parsed = out_dir / parsed_path.name
            atomic_json_dump(parsed_posts, out_parsed)
            print(f"[SAVED] Modified parsed metadata written to: {out_parsed}")

    print("\n[SUCCESS] Link repairs successfully completed.")


if __name__ == "__main__":
    main()
