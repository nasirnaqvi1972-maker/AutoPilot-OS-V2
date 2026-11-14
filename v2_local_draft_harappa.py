import os
import sys
import json
import time
import tempfile
from pathlib import Path
import trafilatura
from sanitize_html import sanitize_post_html

UNESCO_URL = "https://whc.unesco.org/en/tentativelists/1878/"
V2_ROOT = Path(__file__).resolve().parent
INVENTORY_FILE = V2_ROOT / "verified_inventory.json"
DRAFTS_DIR = V2_ROOT / "drafts"
TARGET_SITE = "Harappa"



def save_sanitized_draft_html(html_content: str, filename: str) -> Path:
    """Sanitizes draft HTML content according to SEO standards and atomically saves to drafts/."""
    sanitized = sanitize_post_html(html_content)
    dest = DRAFTS_DIR / filename
    atomic_write_text(dest, sanitized)
    print(f"[SEO Sanitized] Draft saved to {dest}")
    return dest

def atomic_write_text(file_path: Path, content: str, encoding: str = "utf-8") -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=file_path.parent, delete=False, encoding=encoding) as tf:
            temp_file = Path(tf.name)
            tf.write(content)
        temp_file.replace(file_path)
    except Exception:
        if temp_file and temp_file.exists():
            try:
                temp_file.unlink()
            except OSError:
                pass
        raise


def main():
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Using hardcoded Tentative URL for {TARGET_SITE}: {UNESCO_URL}")
    print("Searching verified inventory for Post ID...")

    if not INVENTORY_FILE.is_file():
        print(f"ERROR: Inventory file not found: {INVENTORY_FILE}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(INVENTORY_FILE, "r", encoding="utf-8") as f:
            inventory = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse {INVENTORY_FILE}: {e}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"ERROR: Failed to read {INVENTORY_FILE}: {e}", file=sys.stderr)
        sys.exit(1)

    posts = inventory.get("posts", {})
    if not isinstance(posts, dict):
        print(f"ERROR: Expected 'posts' dictionary in {INVENTORY_FILE}.", file=sys.stderr)
        sys.exit(1)

    post_id = None
    target_lower = TARGET_SITE.lower()
    for pid, data in posts.items():
        if isinstance(data, dict):
            title = data.get("title", "")
            if isinstance(title, str) and target_lower in title.lower():
                post_id = pid
                print(f"Found Post: {title} (ID: {post_id})")
                break

    if not post_id:
        print(f"ERROR: {TARGET_SITE} not found in Blogger inventory.", file=sys.stderr)
        sys.exit(1)

    print(f"Scraping UNESCO source...")
    time.sleep(1)

    downloaded = None
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            downloaded = trafilatura.fetch_url(UNESCO_URL)
            if downloaded:
                break
        except Exception as e:
            print(f"WARNING: Fetch attempt {attempt} failed: {e}", file=sys.stderr)
        if attempt < max_retries:
            time.sleep(2)

    if not downloaded:
        print("ERROR: Could not download UNESCO page after retries.", file=sys.stderr)
        sys.exit(1)

    try:
        text = trafilatura.extract(downloaded)
    except Exception as e:
        print(f"ERROR: Trafilatura extraction raised an exception: {e}", file=sys.stderr)
        sys.exit(1)

    if not text:
        print("ERROR: Could not extract text from downloaded content.", file=sys.stderr)
        sys.exit(1)

    source_file = DRAFTS_DIR / f"{target_lower}_unesco_source.txt"
    try:
        atomic_write_text(source_file, text)
    except OSError as e:
        print(f"ERROR: Failed to write output file {source_file}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\nSUCCESS: Source text saved to {source_file}")
    print(f"Post ID for {TARGET_SITE} is: {post_id}")


if __name__ == "__main__":
    main()
