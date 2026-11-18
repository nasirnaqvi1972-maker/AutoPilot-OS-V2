#!/usr/bin/env python3
"""
auto_inject_images.py - Automatically inject Wikimedia images into posts with <7 images
"""

import argparse
import json
import os
import re
import shutil
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

SNAPSHOT_PATH = Path(r"D:\Projects\AutoPilot_OS_v2\content\image_audit_20261020\audit_v2_posts_snapshot.json")
BACKUP_DIR = Path(r"D:\Projects\AutoPilot_OS_v2\backups")

# Target posts from IMAGE_REPORT.md
TARGET_POST_IDS = [
    "5156852846229382939",  # Taxila - 0 images
    "4931793655886371893",  # Al Qal'a of Beni Hammad - 1
    "3693907016232130527",  # Puran Bhagat Well - 1
    "1074515281431789331",  # Kusak Fort - 1
    "9216206703425015332",  # Acropolis - 2
    "1489848893964608249",  # Aldabra Atoll - 4
    "6863391991573859535",  # Meidan Emam, Isfahan - 5
    "6912849094938699997",  # Victoria Gun of Dulmial - 6
]

TARGET_COUNT = 7
RELAY_URL = "https://wikimedia-relay.nasirabbasnaqvi.workers.dev"
RELAY_TOKEN = "ddd-secret-2026"
WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "DustAndDynastyBot/1.0 (https://dustanddynasty.blogspot.com)"


def _relay_get(target_url, timeout=30):
    params = urllib.parse.urlencode({"url": target_url, "token": RELAY_TOKEN})
    req = urllib.request.Request(f"{RELAY_URL}?{params}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def build_search_query(title):
    """Extract keywords from title for Wikimedia search."""
    # Remove common stop words and markers
    stop_words = {"the", "and", "of", "in", "a", "an", "to", "for", "with", "on", "at", "by", "from", "or", "as", "is", "it", "that", "this", "was", "were", "be", "been", "have", "has", "had", "will", "would", "could", "should", "may", "might", "must", "can", "who", "whom", "whose", "which", "what", "where", "when", "why", "how", "all", "any", "some", "no", "not", "but", "if", "then", "else", "than", "so", "such", "only", "own", "same", "too", "very", "just", "now", "also", "more", "most", "other", "many", "much", "few", "little", "old", "new", "first", "last", "long", "short", "high", "low", "big", "small", "large", "great", "un", "de", "la", "le", "el", "los", "las", "del", "al"}
    
    # Clean title: remove em dashes, pipes, special chars
    cleaned = re.sub(r'[—|]', ' ', title)
    cleaned = re.sub(r'[^\w\s]', ' ', cleaned)
    
    # Get meaningful words
    words = []
    for w in cleaned.split():
        w_lower = w.lower()
        if len(w_lower) >= 3 and w_lower not in stop_words and not w_lower.isdigit():
            words.append(w)
    
    # Take top 5 keywords
    return ' '.join(words[:5])


def build_fallback_queries(title):
    """Generate multiple search queries as fallbacks."""
    queries = []
    
    # Primary query
    queries.append(build_search_query(title))
    
    # Secondary: just the main subject (first 2-3 meaningful words)
    cleaned = re.sub(r'[—|]', ' ', title)
    cleaned = re.sub(r'[^\w\s]', ' ', cleaned)
    words = [w for w in cleaned.split() if len(w) >= 3 and w.lower() not in {"the", "and", "of", "in", "a", "an", "to", "for", "with", "on", "at", "by", "from", "or", "as", "is", "it", "that", "this", "was", "were", "be", "been", "have", "has", "had", "will", "would", "could", "should", "may", "might", "must", "can", "who", "whom", "whose", "which", "what", "where", "when", "why", "how"}]
    if len(words) >= 2:
        queries.append(' '.join(words[:3]))
    
    # Tertiary: just the first significant word + "site" or "monument"
    if words:
        queries.append(f"{words[0]} site")
        queries.append(f"{words[0]} monument")
        queries.append(f"{words[0]} landscape")
    
    # Quaternary: split on comma/colon and take first part
    for sep in [',', ':', '|', '—']:
        if sep in title:
            first_part = title.split(sep)[0].strip()
            if len(first_part) > 3:
                queries.append(build_search_query(first_part))
            break
    
    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for q in queries:
        if q and q not in seen:
            seen.add(q)
            unique.append(q)
    
    return unique


def fetch_wikimedia_images(query, limit=10):
    """Query Wikimedia Commons API for images matching query via relay."""
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": "6",  # File namespace
        "gsrlimit": str(limit),
        "prop": "imageinfo",
        "iiprop": "url|size|mime",
        "iiurlwidth": "1600",
        "format": "json",
        "formatversion": "2",
    }
    
    api_url = WIKIMEDIA_API + "?" + urllib.parse.urlencode(params)
    
    try:
        raw = _relay_get(api_url)
        data = json.loads(raw.decode('utf-8'))
    except Exception as e:
        print(f"  [WARN] Wikimedia API error: {e}")
        return []
    
    images = []
    for page in data.get("query", {}).get("pages", []):
        if "imageinfo" in page:
            info = page["imageinfo"][0]
            mime = info.get("mime", "")
            if mime not in ("image/jpeg", "image/png", "image/webp"):
                continue
            width = info.get("width", 0)
            height = info.get("height", 0)
            if width < 800 or height < 600:
                continue
            # Prefer the original URL or thumb URL
            img_url = info.get("url") or info.get("thumburl")
            if img_url:
                images.append({
                    "url": img_url,
                    "title": page.get("title", ""),
                    "width": width,
                    "height": height,
                })
    
    return images


def fetch_with_fallbacks(title, needed):
    """Try multiple search queries until we get enough images."""
    all_images = []
    seen_urls = set()
    
    for query in build_fallback_queries(title):
        print(f"    Trying query: '{query}'")
        images = fetch_wikimedia_images(query, limit=needed + 5)
        
        for img in images:
            if img["url"] not in seen_urls:
                seen_urls.add(img["url"])
                all_images.append(img)
        
        if len(all_images) >= needed:
            break
    
    return all_images


def inject_images(html, image_urls, post_title):
    """Append image gallery to the end of post content."""
    soup = BeautifulSoup(html, "html.parser")
    
    # Create gallery div
    gallery = soup.new_tag("div")
    gallery["class"] = "image-gallery"
    gallery["style"] = "margin-top: 32px; display: flex; flex-wrap: wrap; gap: 16px;"
    
    for url in image_urls:
        img = soup.new_tag("img")
        img["src"] = url
        img["alt"] = post_title
        img["style"] = "max-width: 100%; height: auto; width: 400px;"
        gallery.append(img)
    
    # Append to body or end of document
    body = soup.find("body")
    if body:
        body.append(gallery)
    else:
        soup.append(gallery)
    
    return str(soup)


def timestamp():
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def atomic_write(path, text):
    tmp = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Auto-inject Wikimedia images into posts with <7 images")
    parser.add_argument("--in-place", action="store_true", help="Write changes to snapshot")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done (default)")
    args = parser.parse_args()
    
    if not args.in_place and not args.dry_run:
        args.dry_run = True
    
    with open(SNAPSHOT_PATH, 'r', encoding='utf-8') as f:
        posts = json.load(f)
    
    # Filter to target posts
    target_posts = [p for p in posts if p.get("id") in TARGET_POST_IDS]
    print(f"Processing {len(target_posts)} target posts...")
    
    total_added = 0
    modified_posts = []
    
    for post in target_posts:
        pid = post.get("id")
        title = post.get("title", "")
        content = post.get("content", "")
        
        soup = BeautifulSoup(content, "html.parser")
        current_count = len(soup.find_all("img"))
        needed = TARGET_COUNT - current_count
        
        if needed <= 0:
            print(f"  {pid}: Already has {current_count} images (target {TARGET_COUNT})")
            continue
        
        print(f"  {pid}: '{title[:60]}' - has {current_count}, need {needed} more")
        
        # Search for images with fallback queries
        images = fetch_with_fallbacks(title, needed)
        
        if not images:
            print(f"    [WARN] No images found for any query")
            continue
        
        # Take only what we need
        selected = images[:needed]
        urls = [img["url"] for img in selected]
        
        # Inject into HTML
        new_html = inject_images(content, urls, title)
        
        post["content"] = new_html
        modified_posts.append(pid)
        total_added += len(selected)
        print(f"    Added {len(selected)} images")
    
    print(f"\nTotal images added: {total_added}")
    print(f"Posts modified: {len(modified_posts)}")
    
    if args.dry_run:
        print("\nDRY RUN - no changes written. Use --in-place to persist.")
        return
    
    # Backup
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / f"audit_v2_posts_snapshot.{timestamp()}.bak"
    shutil.copy2(SNAPSHOT_PATH, backup_path)
    print(f"Backup: {backup_path}")
    
    # Atomic write
    atomic_write(SNAPSHOT_PATH, json.dumps(posts, ensure_ascii=False, indent=2))
    print(f"Updated: {SNAPSHOT_PATH}")


if __name__ == "__main__":
    main()