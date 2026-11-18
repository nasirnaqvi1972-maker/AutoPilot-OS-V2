"""fix_wikimedia_attribution.py

Add Wikimedia Commons attribution captions to images in a Blogger post snapshot.

For every <img> whose src contains upload.wikimedia.org, insert a small
attribution paragraph immediately after the image's parent container (or
immediately after the image itself if it has no element parent), unless an
attributing caption already exists.

Default mode is --dry-run (no files are written). Pass --in-place to
persist changes. Every in-place run first takes a timestamped backup of the
snapshot and writes atomically (temp file + os.replace).

Usage:
    # See what would change (default, safe)
    python fix_wikimedia_attribution.py

    # Actually save changes (with timestamped backup + atomic write)
    python fix_wikimedia_attribution.py --in-place
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

# Match images hosted on Wikimedia Commons.
WIKIMEDIA_IMG_RE = re.compile(r"upload\.wikimedia\.org", re.IGNORECASE)

# Match text that already attributes Wikimedia Commons (avoid duplicate captions).
ATTRIBUTION_RE = re.compile(r"wikimedia commons|image source", re.IGNORECASE)

# The attribution caption inserted after each uncredited Wikimedia image.
ATTRIBUTION_HTML = (
    '<p style="font-size: 0.8em; color: gray; text-align: center;">'
    '<i>Image source: Wikimedia Commons</i></p>'
)


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


def already_attributed(container: Tag) -> bool:
    """
    Return True if *container* (the element an image lives in, or the image
    itself) is already followed by an attributing caption.

    We look at the immediate next sibling: if it's a <p> or <figcaption>
    whose text mentions Wikimedia Commons / "Image source", the image is
    considered already attributed.
    """
    sibling = container.find_next_sibling()
    if sibling is None:
        return False
    if sibling.name not in ("p", "figcaption"):
        return False
    return bool(ATTRIBUTION_RE.search(sibling.get_text(" ", strip=True)))


def insert_attribution(container: Tag) -> None:
    """Insert the attribution <p> immediately after *container*."""
    new_p = BeautifulSoup(ATTRIBUTION_HTML, "html.parser")
    container.insert_after(new_p)


# ---------------------------------------------------------------------------
# Core transformation
# ---------------------------------------------------------------------------

def fix_content(html: str) -> tuple[str, dict]:
    """Apply attribution fixes to one post's HTML. Returns (new_html, stats)."""
    soup = BeautifulSoup(html, "html.parser")

    images_checked = 0
    attributions_added = 0
    skipped_existing = 0

    # Materialise the list so we can mutate the tree while iterating.
    for img in list(soup.find_all("img", src=True)):
        src = img.get("src", "")
        if not WIKIMEDIA_IMG_RE.search(src):
            continue

        images_checked += 1

        # The "parent container" is the image's element parent; if the image
        # is a direct child of <body>/<html> (no real container), fall back to
        # the image itself so we insert after it.
        parent = img.parent
        if parent is None or parent.name in ("body", "html"):
            container = img
        else:
            container = parent

        if already_attributed(container):
            skipped_existing += 1
            continue

        insert_attribution(container)
        attributions_added += 1

    new_html = str(soup)
    stats = {
        "wikimedia_images_checked": images_checked,
        "attributions_added": attributions_added,
        "already_attributed_skipped": skipped_existing,
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
        "wikimedia_images_checked": 0,
        "attributions_added": 0,
        "already_attributed_skipped": 0,
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
            total["wikimedia_images_checked"] += stats["wikimedia_images_checked"]
            total["attributions_added"] += stats["attributions_added"]
            total["already_attributed_skipped"] += stats["already_attributed_skipped"]

    return posts, total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Add Wikimedia Commons attribution captions to images in a Blogger snapshot."
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
    print("Wikimedia attribution scan report")
    print("=" * 68)
    print(f"Snapshot : {snapshot_path}")
    print(f"Mode     : {'IN-PLACE (will write)' if args.in_place else 'DRY-RUN (no writes)'}")
    print(f"Posts scanned            : {stats['posts_scanned']}")
    print(f"Posts affected           : {stats['posts_affected']}")
    print(f"Wikimedia images checked : {stats['wikimedia_images_checked']}")
    print(f"Attributions added       : {stats['attributions_added']}")
    print(f"Already attributed (skip): {stats['already_attributed_skipped']}")
    print("=" * 68)

    if not stats["posts_affected"]:
        print("No missing Wikimedia attributions found. Nothing to do.")
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
