#!/usr/bin/env python3
"""fix_double_h1.py — Convert duplicate <h1> tags to <h2> in 6 specific posts.

Reads content/image_audit_20261020/audit_v2_posts_snapshot.json, targets only
the 6 listed post titles/URLs, and converts every <h1> inside each post's
content field to <h2> using BeautifulSoup.

Flags:
  --dry-run   Report what would change without writing anything.
  --in-place  Write changes to the JSON file with an atomic backup.
"""

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

TARGETS = [
    {"title": "Lower Valley of the Omo"},
    {"title": "Agra Fort", "url": "agra-fort-red-citadel-of-mughals"},
    {"title": "Historic Centre of Avignon"},
    {"title": "Gulf of Porto"},
    {"title": "Elephanta Caves"},
    {"title": "City of Potos\u00ed"},
]

SNAPSHOT_PATH = Path(
    "content/image_audit_20261020/audit_v2_posts_snapshot.json"
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def _is_target(post: dict, target: dict) -> bool:
    title = _normalize(post.get("title", ""))
    target_title = _normalize(target["title"])
    if not title.startswith(target_title):
        return False
    if "url" in target:
        url = _normalize(post.get("url", ""))
        if target["url"] not in url:
            return False
    return True


def _convert_h1_to_h2(html: str):
    soup = BeautifulSoup(html, "html.parser")
    h1_tags = soup.find_all("h1")
    count = len(h1_tags)
    for tag in h1_tags:
        tag.name = "h2"
    return str(soup), count


def _atomic_write(path: Path, data: str) -> None:
    path = path.resolve()
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _backup(path: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = path.with_name(f"{path.name}.bak-{ts}")
    if path.exists():
        backup_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return backup_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert <h1> to <h2> in 6 target posts."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report changes without writing anything.",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Write changes to the JSON file with an atomic backup.",
    )
    args = parser.parse_args()

    if not args.dry_run and not args.in_place:
        parser.error("Either --dry-run or --in-place is required.")

    if not SNAPSHOT_PATH.exists():
        print("ERROR: Snapshot not found: " + str(SNAPSHOT_PATH), file=sys.stderr)
        return 1

    raw = SNAPSHOT_PATH.read_text(encoding="utf-8")
    posts = json.loads(raw)

    matched = []
    missing = []
    for target in TARGETS:
        found = [p for p in posts if _is_target(p, target)]
        if found:
            matched.extend(found)
        else:
            missing.append(target["title"])

    changed_any = False
    seen_ids = set()
    for post in matched:
        pid = post.get("id")
        if pid in seen_ids:
            continue
        seen_ids.add(pid)
        title = post.get("title", "Unknown")
        content = post.get("content", "")
        new_content, count = _convert_h1_to_h2(content)
        if count > 0:
            changed_any = True
            url = post.get("url", "")
            print("[TARGET] " + title + " (" + url + ") — " + str(count) + " <h1> tag(s) -> <h2>")
            if args.in_place:
                post["content"] = new_content
        else:
            print("[OK]     " + title + " — no <h1> tags found (already clean)")

    if missing:
        print("[NOT FOUND in snapshot]: " + ", ".join(missing))

    if not changed_any:
        print("No changes needed across the 6 target posts.")
        return 0

    if args.dry_run:
        print("\n[DRY-RUN] No files were modified. Re-run with --in-place to apply.")
        return 0

    if args.in_place:
        backup_path = _backup(SNAPSHOT_PATH)
        print("[BACKUP] Created: " + str(backup_path))
        updated = json.dumps(posts, ensure_ascii=False, indent=2)
        _atomic_write(SNAPSHOT_PATH, updated)
        print("[WRITE]  Updated: " + str(SNAPSHOT_PATH))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
