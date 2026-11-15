# -*- coding: utf-8 -*-
"""
fix_duplicate_images.py — Auto-Fix Blogger Duplicate & Repeated Images
======================================================================
1. Replaces cross-post duplicate image in Ouro Preto (Post ID: 6222766435592613746)
   by fetching a unique high-res image of Igreja Matriz de Nossa Senhora do Pilar
   via Wikimedia Commons Relay with CC BY-SA 4.0 attribution.
2. Deduplicates intra-post image repetitions across the 5 affected posts
   (Shibam, Konârak, Plitvice, Mesa Verde, Yellowstone), retaining the first
   instance and cleanly pruning subsequent duplicate figure/img blocks.
3. Performs automated HTML backups before updating any post.

Author: Antigravity (EGM Elephant Mode)
"""

import os
import sys
import io
import json
import time
import datetime
import urllib.parse
import urllib.request
from pathlib import Path
from bs4 import BeautifulSoup

# Ensure UTF-8 output on Windows console
if sys.stdout and sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass

V2_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(V2_ROOT))

from core.blogger_publisher import get_blogger_service, execute_with_retry

BLOG_URL = "https://dustanddynasty.blogspot.com"
BACKUP_DIR = V2_ROOT / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Relay configuration (AGENTS.md Rule 8)
RELAY_URL = "https://wikimedia-relay.nasirabbasnaqvi.workers.dev"
RELAY_TOKEN = "ddd-secret-2026"
WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"

# Posts with intra-post repetitions identified during audit
INTRA_REPEAT_POST_IDS = [
    "5872828403351303540",  # Shibam
    "3986801303476041706",  # Konârak
    "7553872700625619797",  # Plitvice
    "1023870585161043628",  # Mesa Verde
    "8246076384848086098",  # Yellowstone
]

OURO_PRETO_POST_ID = "6222766435592613746"
CATBOX_TARGET_SUBSTRING = "sr9j5u"


def safe_print(msg: str):
    """Print safely to Windows console."""
    try:
        print(msg)
    except UnicodeEncodeError:
        safe = msg.encode("cp1252", errors="replace").decode("cp1252")
        print(safe)


def _relay_get(target_url: str, timeout: int = 30) -> bytes:
    """Fetch URL through Cloudflare relay with timeout and token."""
    params = urllib.parse.urlencode({"url": target_url, "token": RELAY_TOKEN})
    req = urllib.request.Request(
        f"{RELAY_URL}?{params}",
        headers={"User-Agent": "DustAndDynastyBot/1.0"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def search_wikimedia_image(query: str, exclude_urls=None):
    """
    Queries Wikimedia Commons via Cloudflare relay for an image matching query.
    Returns: (image_url, artist, license_name, license_url)
    """
    if exclude_urls is None:
        exclude_urls = set()

    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": "6",
        "gsrlimit": "10",
        "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata",
        "iiurlwidth": "1280",
        "format": "json",
        "formatversion": "2",
    }
    api_url = WIKIMEDIA_API + "?" + urllib.parse.urlencode(params)
    try:
        raw = _relay_get(api_url)
        data = json.loads(raw.decode("utf-8"))
        pages = data.get("query", {}).get("pages", [])

        for page in pages:
            info = page.get("imageinfo", [{}])[0]
            thumb_url = info.get("thumburl") or info.get("url")
            if not thumb_url or thumb_url in exclude_urls:
                continue

            width = info.get("width", 0)
            height = info.get("height", 0)
            if width < 800 or height < 500:
                continue

            meta = info.get("extmetadata", {})
            artist_raw = meta.get("Artist", {}).get("value", "Wikimedia Commons")
            # Strip HTML tags from artist if any
            artist_soup = BeautifulSoup(artist_raw, "html.parser")
            artist = artist_soup.get_text(strip=True) or "Wikimedia Commons"

            license_short = meta.get("UsageTerms", {}).get("value", "CC BY-SA 4.0")
            license_url = meta.get("LicenseUrl", {}).get("value", "https://creativecommons.org/licenses/by-sa/4.0/")

            return {
                "url": thumb_url,
                "title": page.get("title", ""),
                "artist": artist,
                "license_short": license_short,
                "license_url": license_url
            }

    except Exception as e:
        safe_print(f"  [ERROR] Wikimedia query failed for '{query}': {e}")

    return None


def backup_post_html(post_id: str, title: str, html: str) -> Path:
    """Saves original post HTML to disk before updating (AGENTS.md Rule 10)."""
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_stem = "".join(c if c.isalnum() else "_" for c in title)[:30]
    backup_file = BACKUP_DIR / f"post_{post_id}_{clean_stem}_{ts}.html"
    with open(backup_file, "w", encoding="utf-8") as f:
        f.write(html)
    return backup_file


def fix_cross_post_duplicate(service, blog_id: str):
    """
    Fixes the cross-post duplicate in Ouro Preto (Post ID: 6222766435592613746).
    Replaces the catbox.moe image with a unique Wikimedia image of Nossa Senhora do Pilar.
    """
    safe_print(f"\n[1/2] Resolving Cross-Post Duplicate in Ouro Preto (Post ID: {OURO_PRETO_POST_ID})...")
    post = execute_with_retry(service.posts().get(blogId=blog_id, postId=OURO_PRETO_POST_ID))
    title = post.get("title", "Historic Town of Ouro Preto")
    html = post.get("content", "")

    soup = BeautifulSoup(html, "html.parser")

    # Find the catbox image
    target_img = None
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if CATBOX_TARGET_SUBSTRING in src:
            target_img = img
            break

    if not target_img:
        safe_print("  [WARN] Catbox duplicate image not found in Ouro Preto post. Already fixed?")
        return

    # Collect existing image URLs in Ouro Preto so we don't pick a duplicate
    existing_urls = {img.get("src") for img in soup.find_all("img") if img.get("src")}

    # Query Wikimedia Commons for Nossa Senhora do Pilar Ouro Preto
    safe_print("  [*] Querying Wikimedia Commons relay for Igreja Matriz de Nossa Senhora do Pilar...")
    result = search_wikimedia_image("Igreja Matriz de Nossa Senhora do Pilar Ouro Preto", exclude_urls=existing_urls)

    if not result:
        safe_print("  [*] Fallback query: 'Ouro Preto Brazil'...")
        result = search_wikimedia_image("Ouro Preto Brazil", exclude_urls=existing_urls)

    if not result:
        safe_print("  [FAIL] Could not find a suitable replacement image on Wikimedia Commons.")
        return

    safe_print(f"  [OK] Found unique replacement image: {result['title']}")
    safe_print(f"       URL: {result['url']}")
    safe_print(f"       Artist: {result['artist']} | License: {result['license_short']}")

    # Backup original post
    backup_file = backup_post_html(OURO_PRETO_POST_ID, title, html)
    safe_print(f"  [Backup] Preserved original HTML -> {backup_file}")

    # Replace image src and attributes
    target_img["src"] = result["url"]
    target_img["alt"] = "Interior of Igreja Matriz de Nossa Senhora do Pilar in Ouro Preto, Minas Gerais, Brazil"
    target_img["title"] = "Igreja Matriz de Nossa Senhora do Pilar - Ouro Preto"

    # Update or insert figcaption with proper CC attribution
    fig = target_img.find_parent("figure")
    if fig:
        figcaption = fig.find("figcaption")
        attr_text = f'Interior of Igreja Matriz de Nossa Senhora do Pilar. Image: {result["artist"]} / <a href="{result["license_url"]}" target="_blank" rel="noopener noreferrer">{result["license_short"]}</a>'
        if figcaption:
            figcaption.clear()
            caption_soup = BeautifulSoup(attr_text, "html.parser")
            figcaption.append(caption_soup)
        else:
            caption_tag = soup.new_tag("figcaption", style="font-size: 11px; color: #777; text-align: center; margin-top: 8px;")
            caption_tag.append(BeautifulSoup(attr_text, "html.parser"))
            fig.append(caption_tag)

    # Patch post to Blogger API
    safe_print("  [*] Patching Ouro Preto post on Blogger API...")
    body = {"content": str(soup)}
    patch_req = service.posts().patch(blogId=blog_id, postId=OURO_PRETO_POST_ID, body=body)
    res = execute_with_retry(patch_req)
    safe_print(f"  [OK] Successfully updated post: {res.get('title')} (ID: {res.get('id')})")


def fix_intra_post_repetitions(service, blog_id: str):
    """
    Fixes the 5 posts with intra-post image repetitions by keeping only the
    first instance of each image and decomposing subsequent identical figures/images.
    """
    safe_print(f"\n[2/2] Resolving Intra-Post Image Repetitions across {len(INTRA_REPEAT_POST_IDS)} posts...")

    for pid in INTRA_REPEAT_POST_IDS:
        try:
            post = execute_with_retry(service.posts().get(blogId=blog_id, postId=pid))
            title = post.get("title", f"Post {pid}")
            html = post.get("content", "")

            soup = BeautifulSoup(html, "html.parser")
            seen_src = set()
            removed_count = 0

            for img in list(soup.find_all("img")):
                src = img.get("src")
                if not src:
                    continue

                if src in seen_src:
                    # Duplicate found! Remove the containing figure or the img tag
                    fig = img.find_parent("figure")
                    if fig:
                        fig.decompose()
                    else:
                        img.decompose()
                    removed_count += 1
                else:
                    seen_src.add(src)

            if removed_count == 0:
                safe_print(f"  [-] Post '{title}' (ID: {pid}): No duplicate images found. Skipping.")
                continue

            safe_print(f"  [*] Post '{title}' (ID: {pid}):")
            safe_print(f"      Pruning {removed_count} duplicate image instance(s)...")

            # Backup original post
            backup_file = backup_post_html(pid, title, html)
            safe_print(f"      [Backup] Saved to -> {backup_file.name}")

            # Patch updated content
            body = {"content": str(soup)}
            patch_req = service.posts().patch(blogId=blog_id, postId=pid, body=body)
            res = execute_with_retry(patch_req)
            safe_print(f"      [OK] Successfully patched post (ID: {res.get('id')})")

        except Exception as e:
            safe_print(f"  [FAIL] Error processing post ID {pid}: {e}")


def main():
    safe_print("=" * 70)
    safe_print("  DUST & DYNASTY — DUPLICATE IMAGE AUTO-FIX ENGINE")
    safe_print(f"  Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    safe_print("=" * 70)

    safe_print("[*] Connecting to Blogger API...")
    service = get_blogger_service()
    blog_req = service.blogs().getByUrl(url=BLOG_URL)
    blog = execute_with_retry(blog_req)
    blog_id = blog["id"]
    safe_print(f"[OK] Connected to Blog ID: {blog_id}")

    # Fix 1: Cross-post duplicate
    fix_cross_post_duplicate(service, blog_id)

    # Fix 2: Intra-post repetitions
    fix_intra_post_repetitions(service, blog_id)

    safe_print("\n" + "=" * 70)
    safe_print("  ALL DUPLICATE REPAIR OPERATIONS COMPLETED")
    safe_print("=" * 70)


if __name__ == "__main__":
    main()
