import os
import sys
import re
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core.blogger_publisher import get_blogger_service
from sanitize_html import sanitize_post_html

PENDING = ROOT / "content" / "pending"
BLOG_URL = "https://dustanddynasty.blogspot.com"
TARGETS = ["avignon", "porto", "blenheim"]


def sanitize_slug(title: str, fallback_id: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:80]
    if not slug:
        slug = f"draft-{fallback_id}"
    return f"{slug}.html"


def remove_images(soup: BeautifulSoup) -> None:
    # Identify containers (e.g. Blogger separator divs or standalone image links)
    containers = set()
    for img in soup.find_all("img"):
        sep = img.find_parent("div", class_="separator")
        if sep:
            containers.add(sep)
        else:
            parent_a = img.find_parent("a")
            if parent_a and not parent_a.get_text(strip=True):
                containers.add(parent_a)
            else:
                containers.add(img)

    # Decompose top-level containers safely without double-decomposing children
    for el in containers:
        if el.parent is not None:
            el.decompose()

    # Clean up any remaining orphaned img tags
    for img in soup.find_all("img"):
        if img.parent is not None:
            img.decompose()


def ensure_head_metadata(soup: BeautifulSoup, title: str) -> None:
    head = soup.find("head")
    if not head:
        head = soup.new_tag("head")
        soup.insert(0, head)

    if not head.find("title"):
        t = soup.new_tag("title")
        t.string = title
        head.append(t)

    if not head.find("meta", attrs={"name": "description"}):
        meta = soup.new_tag("meta", attrs={"name": "description", "content": title[:150]})
        head.append(meta)


def pull_drafts():
    PENDING.mkdir(parents=True, exist_ok=True)

    try:
        service = get_blogger_service()
        blog = service.blogs().getByUrl(url=BLOG_URL).execute()
        blog_id = blog["id"]
    except Exception as e:
        print(f"[PULL] ERROR: Failed to connect to Blogger API: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[PULL] Fetching drafts with pagination and full bodies...")
    all_drafts = []
    page_token = None

    while True:
        try:
            req = service.posts().list(
                blogId=blog_id,
                status="DRAFT",
                fetchBodies=True,
                maxResults=50,
                pageToken=page_token,
            )
            res = req.execute()
        except Exception as e:
            print(f"[PULL] ERROR: Failed to retrieve drafts: {e}", file=sys.stderr)
            sys.exit(1)

        items = res.get("items", [])
        all_drafts.extend(items)
        page_token = res.get("nextPageToken")
        if not page_token:
            break

    print(f"[PULL] Found {len(all_drafts)} total draft(s). Scanning for targets: {TARGETS}")

    matched_targets = set()
    saved_count = 0

    for d in all_drafts:
        title = d.get("title", "")
        matching = [t for t in TARGETS if t in title.lower()]
        if not matching:
            continue

        matched_targets.update(matching)
        post_id = d.get("id", "unknown")
        slug = sanitize_slug(title, post_id)

        content = d.get("content", "")
        soup = BeautifulSoup(content, "html.parser")

        remove_images(soup)
        ensure_head_metadata(soup, title)

        sanitized_html = sanitize_post_html(str(soup))
        out = PENDING / slug
        try:
            out.write_text(sanitized_html, encoding="utf-8")
            saved_count += 1
            print(f"[PULL] Saved {slug} to pending (images removed).")
        except OSError as e:
            print(f"[PULL] ERROR: Failed to write {out}: {e}", file=sys.stderr)

    unmatched = set(TARGETS) - matched_targets
    if unmatched:
        print(f"[PULL] WARNING: The following target(s) were not found in drafts: {sorted(unmatched)}")

    print(f"[PULL] Completed. Successfully saved {saved_count} file(s).")


if __name__ == "__main__":
    pull_drafts()
