"""
fix_html_anomalies.py
=====================
Cleans three categories of HTML anomalies from audit_v2_posts_snapshot.json:

  1. Empty heading tags  — <h1/h2/h3/h4/h5/h6> with no text or images inside.
  2. Empty anchor tags   — <a href="..."> with no text or images inside.
  3. Excess <br> runs    — 3+ consecutive <br> tags collapsed to exactly 2.

Safety features (consistent with other pipeline scripts):
  --dry-run   (DEFAULT) — reports changes only; never writes.
  --in-place            — backs up snapshot with a timestamp, then overwrites it.
  --output-dir DIR      — writes a modified copy to DIR instead (non-destructive).
  --post-id  ID         — restrict fix to a single post ID (for spot-checking).

Usage:
  python fix_html_anomalies.py                        # dry-run all posts
  python fix_html_anomalies.py --post-id 4931793655886371893  # dry-run one post
  python fix_html_anomalies.py --in-place             # apply to snapshot (with backup)
  python fix_html_anomalies.py --output-dir fixed/    # write to a separate directory
"""

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

try:
    from bs4 import BeautifulSoup, NavigableString, Tag
except ImportError:
    print("[ERROR] BeautifulSoup4 is not installed in the venv.")
    print("        Run:  pip install beautifulsoup4")
    raise SystemExit(1)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent
SNAPSHOT_PATH = PROJECT_ROOT / "content" / "image_audit_20261020" / "audit_v2_posts_snapshot.json"
HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
MIN_BR_RUN = 3          # runs of this many (or more) consecutive <br>s are reduced
MAX_BR_ALLOWED = 2      # …down to this many


# ---------------------------------------------------------------------------
# Fix helpers
# ---------------------------------------------------------------------------

def _has_content(tag: Tag) -> bool:
    """Return True if a tag contains visible text OR an image (non-empty)."""
    if tag.find("img"):
        return True
    text = tag.get_text(strip=True)
    return bool(text)


def fix_empty_headings(soup: BeautifulSoup) -> list[str]:
    """Remove heading tags that carry no text and no images. Returns change log."""
    changes = []
    for tag in soup.find_all(HEADING_TAGS):
        if not _has_content(tag):
            changes.append(f"Removed empty <{tag.name}> tag: {str(tag)[:80]!r}")
            tag.decompose()
    return changes


def fix_empty_anchors(soup: BeautifulSoup) -> list[str]:
    """
    Remove <a> tags that carry no text and no images.

    Safelist: anchors with a 'name' attribute (e.g. <a name="more"></a>) are
    intentional in-page jump targets used by Blogger and other CMSes.
    They are skipped even if they have no visible content.

    Returns change log.
    """
    changes = []
    for tag in soup.find_all("a"):
        # Skip named anchors — they are page-jump markers, not broken links
        if tag.get("name") is not None:
            continue
        if not _has_content(tag):
            changes.append(f"Removed empty <a href={tag.get('href','')!r}>: {str(tag)[:80]!r}")
            tag.decompose()
    return changes


def fix_excess_br(soup: BeautifulSoup) -> list[str]:
    """
    Collapse runs of MIN_BR_RUN+ consecutive <br> elements down to MAX_BR_ALLOWED.
    'Consecutive' means only whitespace-only NavigableStrings may appear between them.
    Returns change log.
    """
    changes = []
    all_brs = soup.find_all("br")
    visited = set()

    for br in all_brs:
        if id(br) in visited:
            continue

        # Collect the consecutive-br run starting at this br
        run = [br]
        sibling = br.next_sibling
        while sibling is not None:
            if isinstance(sibling, NavigableString):
                if sibling.strip() == "":
                    sibling = sibling.next_sibling
                    continue
                else:
                    break  # non-whitespace text — run ends
            if isinstance(sibling, Tag) and sibling.name == "br":
                run.append(sibling)
                sibling = sibling.next_sibling
            else:
                break

        if len(run) >= MIN_BR_RUN:
            # Mark all as visited
            for b in run:
                visited.add(id(b))

            extras = run[MAX_BR_ALLOWED:]  # everything beyond the first MAX_BR_ALLOWED
            changes.append(
                f"Collapsed run of {len(run)} <br> tags to {MAX_BR_ALLOWED} "
                f"(removed {len(extras)} excess)"
            )
            for b in extras:
                b.decompose()

    return changes


# ---------------------------------------------------------------------------
# Per-post processing
# ---------------------------------------------------------------------------

def process_post(post: dict, dry_run: bool) -> tuple[dict, list[str]]:
    """
    Analyse (and optionally fix) one post dict.
    Returns (possibly-modified post dict, list of human-readable change strings).
    """
    content = post.get("content", "")
    if not content:
        return post, []

    soup = BeautifulSoup(content, "html.parser")

    all_changes: list[str] = []
    all_changes += fix_empty_headings(soup)
    all_changes += fix_empty_anchors(soup)
    all_changes += fix_excess_br(soup)

    if all_changes and not dry_run:
        # lxml wraps content in <html><body>; extract just the body's children
        body = soup.find("body")
        new_html = "".join(str(child) for child in body.children) if body else str(soup)
        post = {**post, "content": new_html}

    return post, all_changes


# ---------------------------------------------------------------------------
# Atomic write
# ---------------------------------------------------------------------------

def atomic_write_json(path: Path, data: object) -> None:
    """Write JSON to a temp file in the same directory, then rename atomically."""
    tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Backup helper
# ---------------------------------------------------------------------------

def backup(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = path.with_suffix(f".bak-{stamp}{path.suffix}")
    shutil.copy2(path, dest)
    return dest


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Fix empty headings, empty anchors, and excess <br> runs in the post snapshot.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--snapshot",
        default=str(SNAPSHOT_PATH),
        help="Path to audit_v2_posts_snapshot.json (default: %(default)s)",
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument(
        "--in-place",
        action="store_true",
        help="Apply fixes directly to the snapshot file (creates timestamped backup first).",
    )
    mode.add_argument(
        "--output-dir",
        metavar="DIR",
        help="Write modified snapshot to this directory (non-destructive).",
    )
    p.add_argument(
        "--post-id",
        metavar="ID",
        help="Restrict processing to a single post ID.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="(DEFAULT) Report changes without writing anything.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # Resolve write mode
    write_mode: str  # "dry", "in-place", "output-dir"
    if args.in_place:
        write_mode = "in-place"
        args.dry_run = False
    elif args.output_dir:
        write_mode = "output-dir"
        args.dry_run = False
    else:
        write_mode = "dry"
        args.dry_run = True

    snapshot_path = Path(args.snapshot).resolve()

    # --- Load snapshot ---
    print(f"[INIT] Loading snapshot: {snapshot_path}")
    if not snapshot_path.exists():
        print(f"[ERROR] Snapshot not found: {snapshot_path}")
        raise SystemExit(1)

    try:
        raw = snapshot_path.read_text(encoding="utf-8")
        posts: list[dict] = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"[ERROR] Invalid JSON in snapshot: {exc}")
        raise SystemExit(1)

    if not isinstance(posts, list):
        print("[ERROR] Snapshot root must be a JSON array.")
        raise SystemExit(1)

    # --- Filter by --post-id ---
    if args.post_id:
        filtered = [p for p in posts if str(p.get("id", "")) == args.post_id]
        if not filtered:
            print(f"[ERROR] No post found with id={args.post_id!r}")
            raise SystemExit(1)
        process_set = filtered
        is_subset = True
    else:
        process_set = posts
        is_subset = False

    # --- Mode banner ---
    if write_mode == "dry":
        print("[MODE] DRY RUN — no files will be modified.")
    elif write_mode == "in-place":
        print("[MODE] IN-PLACE — snapshot will be overwritten (backup created first).")
    else:
        print(f"[MODE] OUTPUT-DIR — fixed snapshot written to: {args.output_dir}")

    print(f"[INFO] Posts to process: {len(process_set)}")
    print()

    # --- Process posts ---
    total_changes = 0
    total_posts_changed = 0
    modified_posts: dict[str, dict] = {}  # id -> modified post dict

    for i, post in enumerate(process_set, 1):
        post_id = str(post.get("id", "unknown"))
        title = post.get("title", "(no title)")[:70]

        updated_post, changes = process_post(post, dry_run=args.dry_run)

        if changes:
            total_posts_changed += 1
            total_changes += len(changes)
            modified_posts[post_id] = updated_post
            print(f"  [{i:>3}/{len(process_set)}] {title}")
            for c in changes:
                print(f"           → {c}")
        elif i % 40 == 0 or i == len(process_set):
            print(f"  Progress: {i}/{len(process_set)} posts scanned...")

    # --- Summary ---
    print()
    print("=" * 55)
    print(f"  Posts Scanned:        {len(process_set)}")
    print(f"  Posts With Changes:   {total_posts_changed}")
    print(f"  Total Fixes Applied:  {total_changes}")
    print("=" * 55)
    print()

    if total_changes == 0:
        print("[INFO] No issues found. Nothing to write.")
        return

    if write_mode == "dry":
        print("[DRY RUN] Re-run with --in-place or --output-dir to apply these fixes.")
        return

    # --- Apply fixes to the full posts list ---
    # Merge modified posts back into the master list
    id_to_index = {str(p.get("id", "")): idx for idx, p in enumerate(posts)}
    for post_id, updated in modified_posts.items():
        if post_id in id_to_index:
            posts[id_to_index[post_id]] = updated
        # If processing a subset that isn't in the master list (shouldn't happen), skip

    # If we filtered to a subset, only the matched post(s) are in posts already
    # (they were updated in-place via id_to_index above), so `posts` is always the full list.

    # --- Write output ---
    if write_mode == "in-place":
        bak = backup(snapshot_path)
        print(f"[BACKUP] {bak.name}")
        atomic_write_json(snapshot_path, posts)
        print(f"[SAVED]  {snapshot_path}")

    elif write_mode == "output-dir":
        out_dir = Path(args.output_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / snapshot_path.name
        atomic_write_json(out_path, posts)
        print(f"[SAVED]  {out_path}")

    print("\n[DONE] Fix complete.")


if __name__ == "__main__":
    main()
