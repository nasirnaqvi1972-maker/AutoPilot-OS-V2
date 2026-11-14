"""
v2_safe_bulk_push.py
LIVE MODE. Updates EXISTING Blogger posts with smart image distribution.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, Tag
from googleapiclient.errors import HttpError

from core.blogger_publisher import get_blogger_service

ROOT = Path(r"D:\Projects\AutoPilot_OS_v2")
INVENTORY_PATH = ROOT / "verified_inventory.json"
DRAFTS_DIR = ROOT / "drafts"
BACKUPS_DIR = ROOT / "backups"
OUTPUT_DIR = ROOT / "safe_push_output"
LOG_PATH = ROOT / "push_log.txt"

# SAFETY SWITCHES
DRY_RUN = True             # Set to False ONLY after verifying on a test blog
MAX_POSTS_PER_RUN = 200   # Process all remaining drafts
RETRY_DELAY_SECONDS = 15  

def setup_logging() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

def load_inventory(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Inventory not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    posts_data = data.get("posts", {}) if isinstance(data, dict) else {}
    cleaned = []
    for post_id, item in posts_data.items():
        if isinstance(item, dict) and item.get("title") and item.get("url"):
            cleaned.append({
                "post_id": str(post_id),
                "title": str(item["title"]),
                "url": str(item["url"]),
            })
    return cleaned

def match_draft_to_post(draft_path: Path, inventory: list[dict[str, Any]]) -> dict[str, Any]:
    stem = draft_path.stem.replace("_revision", "")
    # 1. Prefer exact match
    for item in inventory:
        safe_filename = re.sub(r'[^a-zA-Z0-9]', '_', item["title"])[:30].lower()
        if safe_filename == stem:
            return item
    # 2. Fallback: substring match (warn — can be ambiguous)
    for item in inventory:
        safe_filename = re.sub(r'[^a-zA-Z0-9]', '_', item["title"])[:30].lower()
        if len(stem) > 3 and (stem in safe_filename or safe_filename in stem):
            logging.warning(f"Fuzzy match for {draft_path.name} -> {item['title']} (may be ambiguous)")
            return item
    raise ValueError(f"No match for {draft_path.name}")

def clean_draft_html(raw_html: str) -> str:
    # Aggressive regex to strip everything after the Fact-Check Report or ### 5.
    raw_html = re.split(r'(?i)fact-check report|###\s*5\.', raw_html)[0]
    # Remove trailing dashes, empty lines, or stray marks
    raw_html = re.sub(r'[-—_\s]{3,}$', '', raw_html).strip()

    soup = BeautifulSoup(raw_html, "html.parser")
    
    # Double check and strip HTML Fact-Check Report if it exists
    headings = [tag for tag in soup.find_all(re.compile(r"^h[1-6]$")) if "fact-check" in tag.get_text().casefold()]
    if headings:
        target = headings[0]
        parent = target.parent
        if parent and parent.name in ("article", "main", "body", "div", "section"):
            seen = False
            for child in list(parent.contents):
                if child is target: seen = True
                if seen:
                    if isinstance(child, Tag): child.decompose()
                    else: child.extract()
    
    for tag in soup.find_all(["script", "style"]): tag.decompose()

    body = soup.body
    result = "".join(str(child) for child in (body.contents if body else soup.contents)).strip()
    if not result: raise ValueError("Draft empty after cleanup.")
    return result

def is_image_container(tag: Tag) -> bool:
    if tag.name == "figure" and tag.find("img"): return True
    if tag.name == "div" and "separator" in tag.get("class", []) and tag.find("img"): return True
    return False

def extract_image_units(original_html: str) -> list[str]:
    soup = BeautifulSoup(original_html, "html.parser")
    units = []
    for tag in soup.find_all(is_image_container):
        if any(parent in units for parent in tag.parents): continue
        units.append(tag)
    if not units:
        for img in soup.find_all("img"):
            if any(unit in img.parents for unit in units): continue
            parent = img.find_parent(["a", "p"])
            units.append(parent if parent else img)
            
    seen = set()
    output = []
    for unit in units:
        html = str(unit)
        if html not in seen:
            seen.add(html)
            output.append(html)
    return output

def inject_images_evenly(new_html: str, image_units: list[str]) -> str:
    if not image_units: return new_html

    soup = BeautifulSoup(new_html, "html.parser")
    container = soup.body if soup.body else soup
    
    blocks = container.find_all(['p', 'h2', 'h3', 'ul', 'ol'], recursive=False)
    if not blocks:
        blocks = container.find_all(['p', 'h2', 'h3', 'ul', 'ol'])
        
    if not blocks:
        for unit in image_units:
            fragment = BeautifulSoup(unit, "html.parser")
            for node in list(fragment.contents):
                container.append(deepcopy(node))
        return "".join(str(child) for child in (soup.body.contents if soup.body else soup.contents)).strip()

    num_images = len(image_units)
    num_blocks = len(blocks)
    step = max(1, num_blocks // (num_images + 1))
    
    image_index = 0
    for i, block in enumerate(blocks):
        if image_index >= num_images:
            break
        if (i + 1) % step == 0:
            fragment = BeautifulSoup(image_units[image_index], "html.parser")
            for node in list(fragment.contents):
                block.insert_after(deepcopy(node))
            image_index += 1
            
    while image_index < num_images:
        fragment = BeautifulSoup(image_units[image_index], "html.parser")
        for node in list(fragment.contents):
            container.append(deepcopy(node))
        image_index += 1

    return "".join(str(child) for child in (soup.body.contents if soup.body else soup.contents)).strip()

def process_one(service, blog_id: str, record: dict[str, Any], draft_path: Path) -> None:
    post_id = record["post_id"]
    logging.info(f"Processing: {draft_path.name}")
    
    original = service.posts().get(
        blogId=blog_id, postId=post_id, fields="id,status,content,url,published"
    ).execute()
    
    original_html = original.get("content", "")
    status = original.get("status", "").upper()
    if not status and original.get("published"): status = "LIVE"

    if status != "LIVE":
        logging.warning(f"Skipping {post_id}: Status is '{status}', not LIVE.")
        return

    backup_path = BACKUPS_DIR / f"{post_id}_backup.html"
    backup_path.write_text(original_html, encoding="utf-8")

    draft_raw = draft_path.read_text(encoding="utf-8")
    clean_html = clean_draft_html(draft_raw)
    image_units = extract_image_units(original_html)
    combined_html = inject_images_evenly(clean_html, image_units)

    output_path = OUTPUT_DIR / f"{post_id}_ready.html"
    output_path.write_text(combined_html, encoding="utf-8")

    if DRY_RUN:
        logging.info(f"DRY_RUN: No update for {post_id}")
        return

    body = {"content": combined_html}
    try:
        service.posts().patch(blogId=blog_id, postId=post_id, body=body).execute()
        logging.info(f"SUCCESS: Live post {post_id} updated.")
        time.sleep(2) 
    except HttpError as e:
        if e.resp.status == 429:
            logging.warning("Rate limit hit. Sleeping 15 seconds...")
            time.sleep(RETRY_DELAY_SECONDS)
        else:
            logging.error(f"FAILED to patch {post_id}: {e}")
    except Exception as e:
        logging.error(f"FAILED to patch {post_id}: {e}")

def main() -> None:
    setup_logging()
    inventory = load_inventory(INVENTORY_PATH)
    draft_paths = sorted(DRAFTS_DIR.glob("*_revision.html"))

    logging.info("Connecting to Blogger API...")
    service = get_blogger_service()
    blog = service.blogs().getByUrl(url='https://dustanddynasty.blogspot.com').execute()
    blog_id = str(blog['id'])

    processed = 0
    for draft_path in draft_paths:
        if processed >= MAX_POSTS_PER_RUN: break
        try:
            record = match_draft_to_post(draft_path, inventory)
            process_one(service, blog_id, record, draft_path)
            processed += 1
        except Exception as e:
            logging.error(f"FAILED {draft_path.name}: {e}")

if __name__ == "__main__":
    main()
