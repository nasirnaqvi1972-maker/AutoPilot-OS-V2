"""nuke_monetization.py

Aggressively strip monetization funnels from a Blogger post snapshot.

Removes:
  1. Any <a> tag whose href contains patreon.com or gumroad.com
     (including subdomains such as www. or dustanddynasty.).
  2. Any <a>, <button>, or <p> tag whose text contains:
     "Buy Me a Coffee", "Buy me a coffee", "Support Dust and Dynasty",
     "pledge", or "donate" (case-insensitive).
  3. Any empty <div> or <p> container left behind after the above removals.

Default mode is --dry-run (no files are written). Pass --in-place to
persist changes. Every in-place run first takes a timestamped backup of
the snapshot and writes atomically (temp file + os.replace).

Usage:
    # See what would change (default, safe)
    python nuke_monetization.py

    # Actually save changes (with timestamped backup + atomic write)
    python nuke_monetization.py --in-place
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

from bs4 import BeautifulSoup, Tag

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_SNAPSHOT = Path(
    r"d:\Projects\AutoPilot_OS_v2\content\image_audit_20261020\audit_v2_posts_snapshot.json"
)

BACKUP_DIR = Path(r"d:\Projects\AutoPilot_OS_v2\backups")

# Match patreon.com / gumroad.com in any href, subdomains allowed.
MONETIZATION_DOMAIN_RE = re.compile(
    r"(?:patreon|gumroad)\.com", re.IGNORECASE
)

# Phrases that, when found inside a tag's text, mark that tag for removal.
# Single words use word boundaries to avoid clobbering legitimate historical
# mentions (e.g. "the emperor donated land"); phrases match literally.
MONETIZATION_TEXT_PATTERNS = [
    re.compile(r"buy\s+me\s+a\s+coffee", re.IGNORECASE),
    re.compile(r"support\s+dust\s+and\s+dynasty", re.IGNORECASE),
    re.compile(r"\bpledge\b", re.IGNORECASE),
    re.compile(r"\bdonate\b", re.IGNORECASE),
]

EMPTY_CONTAINER_TAGS = ("div", "p")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def take_backup(snapshot_path: Path) -> Path:
    """Copy the snapshot to the backups directory with a timestamp."""
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


def tag_has_monetization_text(tag: Tag) -> bool:
    """Return True if *tag*'s visible text contains a monetization phrase."""
    text = tag.get_text(" ", strip=True)
    if not text:
        return False
    return any(p.search(text) for p in MONETIZATION_TEXT_PATTERNS)


def is_empty_container(tag: Tag) -> bool:
    """True if *tag* holds no visible text and no child elements."""
    if tag.get_text(strip=True):
        return False
    if tag.find_all(recursive=False):
        return False
    return True


# ---------------------------------------------------------------------------
# Core transformation
# ---------------------------------------------------------------------------

def fix_content(html: str) -> tuple[str, dict]:
    """Apply monetization removal to one post's HTML.

    Returns (new_html, stats).
    """
    soup = BeautifulSoup(html, "html.parser")

    to_remove: list[Tag] = []

    # --- Pass 1: <a> tags with monetization domains in href --------------
    for a in list(soup.find_all("a", href=True)):
        href = a.get("href", "")
        if MONETIZATION_DOMAIN_RE.search(href):
            to_remove.append(a)

    # --- Pass 2: <a>, <button>, <p> with monetization text ---------------
    for tag in list(soup.find_all(["a", "button", "p"])):
        if tag in to_remove:
            continue
        if tag_has_monetization_text(tag):
            to_remove.append(tag)

    # Count before decomposing: BeautifulSoup's decompose() clears tag.name to ''.
    links_removed = sum(1 for t in to_remove if t.name == "a")
    text_tags_removed = sum(1 for t in to_remove if t.name in ("button", "p"))

    # Remove all marked tags.
    for tag in to_remove:
        tag.decompose()

    # --- Pass 3: iteratively remove empty <div>/<p> containers -----------
    empty_containers_removed = 0
    changed = True
    while changed:
        changed = False
        for container in list(soup.find_all(EMPTY_CONTAINER_TAGS)):
            if not is_empty_container(container):
                continue
            container.decompose()
            empty_containers_removed += 1
            changed = True
            break  # restart scan since the tree changed

    new_html = str(soup)
    stats = {
        "links_removed": links_removed,
        "text_tags_removed": text_tags_removed,
        "empty_containers_removed": empty_containers_removed,
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
        "links_removed": 0,
        "text_tags_removed": 0,
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
            total["links_removed"] += stats["links_removed"]
            total["text_tags_removed"] += stats["text_tags_removed"]
            total["empty_containers_removed"] += stats["empty_containers_removed"]

    return posts, total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Aggressively remove monetization funnels from a Blogger snapshot."
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
    print("Monetization removal scan report")
    print("=" * 68)
    print(f"Snapshot : {snapshot_path}")
    print(f"Mode     : {'IN-PLACE (will write)' if args.in_place else 'DRY-RUN (no writes)'}")
    print(f"Posts scanned              : {stats['posts_scanned']}")
    print(f"Posts affected             : {stats['posts_affected']}")
    print(f"<a> links removed          : {stats['links_removed']}")
    print(f"<button>/<p> text tags removed : {stats['text_tags_removed']}")
    print(f"Empty containers removed   : {stats['empty_containers_removed']}")
    print("=" * 68)

    if not stats["posts_affected"]:
        print("No monetization traces found. Nothing to do.")
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
