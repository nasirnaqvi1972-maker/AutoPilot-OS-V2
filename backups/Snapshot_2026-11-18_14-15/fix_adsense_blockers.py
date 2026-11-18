"""fix_adsense_blockers.py

Fix AdSense compliance blockers in a Blogger post snapshot file.

Default mode is --dry-run (no files are written). Pass --in-place to
persist changes. Every in-place run first takes a timestamped backup of
the snapshot and writes atomically (temp file + os.replace).

Usage:
    # See what would change (default, safe)
    python fix_adsense_blockers.py

    # Actually save changes (with timestamped backup + atomic write)
    python fix_adsense_blockers.py --in-place
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_SNAPSHOT = Path(
    r"d:\Projects\AutoPilot_OS_v2\content\image_audit_20261020\audit_v2_posts_snapshot.json"
)

BACKUP_DIR = Path(r"d:\Projects\AutoPilot_OS_v2\backups")

# Match sentences that contain an AI-disclaimer phrase.
# Covers "As an AI", "as an AI language model", "as an artificial intelligence",
# etc. Case-insensitive; removes the whole sentence including its terminator
# and trailing whitespace so no dangling punctuation is left behind.
AI_DISCLAIMER_RE = re.compile(
    r"[^.!?]*\bas an (?:ai|artificial intelligence)[^.!?]*[.!?]?\s*",
    re.IGNORECASE,
)

# Match patreon.com / gumroad.com URLs (with or without www, http or https).
MONETIZATION_RE = re.compile(
    r"https?://(?:www\.)?(?:patreon|gumroad)\.com", re.IGNORECASE
)

CONTAINER_TAGS = ("p", "div")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def take_backup(snapshot_path: Path) -> Path:
    """Copy the snapshot to the backups directory with a timestamp. Returns backup path."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_name = f"{snapshot_path.stem}.{timestamp()}.bak"
    backup_path = BACKUP_DIR / backup_name
    shutil.copy2(snapshot_path, backup_path)
    return backup_path


def atomic_write_text(path: Path, text: str) -> None:
    """Write text to *path* atomically via a temp file in the same directory."""
    tmp_path = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    try:
        with open(tmp_path, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Core transformations
# ---------------------------------------------------------------------------

def remove_ai_disclaimers(soup: BeautifulSoup) -> int:
    """Remove AI-disclaimer sentences from text nodes. Returns number removed."""
    count = 0
    # Iterate over a snapshot of all text nodes; modifying the tree while
    # walking live nodes is unsafe, so materialise the list first.
    for node in list(soup.find_all(string=True)):
        text = str(node)
        if not AI_DISCLAIMER_RE.search(text):
            continue
        new_text = AI_DISCLAIMER_RE.sub("", text)
        if new_text != text:
            node.replace_with(new_text)
            count += 1
    return count


def strip_monetization_links(soup: BeautifulSoup) -> tuple[int, int]:
    """
    Remove <a> tags linking to patreon.com/gumroad.com, then remove any
    <p>/<div> container that was left empty as a result.

    Returns (links_removed, containers_removed).
    """
    links_removed = 0
    containers_to_check: set = set()

    for a in list(soup.find_all("a", href=True)):
        href = a.get("href", "")
        if not MONETIZATION_RE.search(href):
            continue
        parent = a.parent
        a.decompose()
        links_removed += 1
        if parent is not None and parent.name in CONTAINER_TAGS:
            containers_to_check.add(parent)

    containers_removed = 0
    for parent in list(containers_to_check):
        # Only remove if it's still attached to the tree.
        if parent.parent is None:
            continue
        # Skip containers that still hold meaningful content (text, images,
        # iframes, line breaks, etc.) — only take out truly empty husks.
        if parent.get_text(strip=True):
            continue
        if parent.find_all(["img", "iframe", "br"]):
            continue
        parent.decompose()
        containers_removed += 1

    return links_removed, containers_removed


def fix_content(html: str) -> tuple[str, dict]:
    """Apply all fixes to one post's HTML. Returns (new_html, stats)."""
    soup = BeautifulSoup(html, "html.parser")

    ai_removed = remove_ai_disclaimers(soup)
    links_removed, containers_removed = strip_monetization_links(soup)

    new_html = str(soup)
    stats = {
        "ai_disclaimers_removed": ai_removed,
        "monetization_links_removed": links_removed,
        "empty_containers_removed": containers_removed,
    }
    return new_html, stats


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def load_posts(snapshot_path: Path) -> list[dict]:
    with open(snapshot_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise SystemExit(f"Snapshot root is not a list: {type(data).__name__}")
    return data


def process_posts(posts: list[dict]) -> tuple[list[dict], dict]:
    """Return (updated_posts, aggregate_stats)."""
    total = {
        "posts_scanned": 0,
        "posts_affected": 0,
        "ai_disclaimers_removed": 0,
        "monetization_links_removed": 0,
        "empty_containers_removed": 0,
    }

    for post in posts:
        total["posts_scanned"] += 1
        html = post.get("content", "")
        if not isinstance(html, str) or not html:
            continue

        new_html, stats = fix_content(html)
        if any(stats.values()):
            post["content"] = new_html
            total["posts_affected"] += 1
            total["ai_disclaimers_removed"] += stats["ai_disclaimers_removed"]
            total["monetization_links_removed"] += stats["monetization_links_removed"]
            total["empty_containers_removed"] += stats["empty_containers_removed"]

    return posts, total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Remove AdSense blockers (AI disclaimers, Patreon/Gumroad links) from a Blogger snapshot."
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_SNAPSHOT,
        help="Path to the snapshot JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Actually save changes. Without this flag the script runs in "
        "--dry-run mode and writes nothing.",
    )
    args = parser.parse_args(argv)

    snapshot_path: Path = args.file
    if not snapshot_path.exists():
        print(f"ERROR: snapshot not found: {snapshot_path}", file=sys.stderr)
        return 2

    posts = load_posts(snapshot_path)
    updated_posts, stats = process_posts(posts)

    # --- report -----------------------------------------------------------
    print("=" * 68)
    print("AdSense blocker scan report")
    print("=" * 68)
    print(f"Snapshot : {snapshot_path}")
    print(f"Mode     : {'IN-PLACE (will write)' if args.in_place else 'DRY-RUN (no writes)'}")
    print(f"Posts scanned : {stats['posts_scanned']}")
    print(f"Posts affected: {stats['posts_affected']}")
    print(f"AI disclaimers removed       : {stats['ai_disclaimers_removed']}")
    print(f"Monetization links removed   : {stats['monetization_links_removed']}")
    print(f"Empty containers removed     : {stats['empty_containers_removed']}")
    print("=" * 68)

    if not stats["posts_affected"]:
        print("No AdSense blockers found. Nothing to do.")
        return 0

    if not args.in_place:
        print("Dry-run complete. Re-run with --in-place to persist changes.")
        return 0

    # --- persist ----------------------------------------------------------
    backup_path = take_backup(snapshot_path)
    print(f"Backup written: {backup_path}")

    out_text = json.dumps(updated_posts, ensure_ascii=False, indent=2)
    atomic_write_text(snapshot_path, out_text)
    print(f"Saved changes in-place (atomic write): {snapshot_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
