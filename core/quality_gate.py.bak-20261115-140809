"""core/quality_gate.py

Unified AdSense/SEO compliance engine for AutoPilot OS.
Consolidates monetization removal, attribution injection, and HTML sanitization
into a single pass that runs before every Blogger publish.
"""

from __future__ import annotations

import re
from bs4 import BeautifulSoup, Tag
from urllib.parse import urlsplit

# Re-export the existing sanitize_post_html
from sanitize_html import sanitize_post_html


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Domains that trigger monetization link removal
MONETIZATION_DOMAIN_RE = re.compile(
    r"(?:patreon|gumroad|buymeacoffee|ko-fi|kofi|paypal\.me|liberapay|payhip|sellfy|gum\.co)\.com",
    re.IGNORECASE,
)

# Phrases that mark a tag for removal (with word boundaries for single words)
MONETIZATION_TEXT_PATTERNS = [
    re.compile(r"buy\s+me\s+a\s+coffee", re.IGNORECASE),
    re.compile(r"support\s+(?:me|us|this\s+site|this\s+blog)", re.IGNORECASE),
    re.compile(r"become\s+a\s+patron", re.IGNORECASE),
    re.compile(r"\bpledge\b", re.IGNORECASE),
    re.compile(r"\bdonate\b", re.IGNORECASE),
    re.compile(r"\btip\s+(?:me|us|jar)\b", re.IGNORECASE),
    re.compile(r"coffee\.com", re.IGNORECASE),
]

EMPTY_CONTAINER_TAGS = ("div", "p", "section", "article", "aside")

# Wikimedia Commons images
WIKIMEDIA_IMG_RE = re.compile(r"upload\.wikimedia\.org", re.IGNORECASE)
ATTRIBUTION_RE = re.compile(r"wikimedia commons|cc by|creative commons|image source", re.IGNORECASE)
WIKIMEDIA_ATTR_HTML = (
    '<figcaption style="font-size: 11px; color: #777; text-align: center;">'
    'Image: <a href="https://commons.wikimedia.org">Wikimedia Commons</a> / '
    '<a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a></figcaption>'
)

# Unsplash images
UNSPLASH_IMG_RE = re.compile(r"unsplash\.com", re.IGNORECASE)

# Internal domains for link sanitization (from sanitize_html.py)
INTERNAL_DOMAINS = {
    "dustanddynasty.blogspot.com",
    "blogger.com",
    "www.blogger.com",
    "bp.blogspot.com",
    "blogger.googleusercontent.com",
    "googleusercontent.com",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_external_link(href: str) -> bool:
    """Check if a URL points to an external, third-party domain."""
    if not href:
        return False
    clean_href = href.strip()
    if not clean_href.startswith(("http://", "https://", "//")):
        return False
    parts = urlsplit(clean_href)
    netloc = parts.netloc.lower()
    if not netloc:
        return False
    for domain in INTERNAL_DOMAINS:
        if netloc == domain or netloc.endswith("." + domain):
            return False
    return True


def tag_has_monetization_text(tag: Tag) -> bool:
    """Return True if tag's visible text contains a monetization phrase."""
    text = tag.get_text(" ", strip=True)
    if not text:
        return False
    return any(p.search(text) for p in MONETIZATION_TEXT_PATTERNS)


def is_empty_container(tag: Tag) -> bool:
    """True if tag holds no visible text and no meaningful child elements."""
    if tag.get_text(strip=True):
        return False
    # Check for meaningful children (images, iframes, tables, lists, etc.)
    meaningful_children = tag.find_all(["img", "iframe", "table", "ul", "ol", "figure", "video", "audio"], recursive=False)
    if meaningful_children:
        return False
    # Also check if it has any element children at all
    if tag.find_all(recursive=False):
        return False
    return True


def already_attributed(container: Tag, attr_regex: re.Pattern) -> bool:
    """Check if container already has attribution (sibling or child figcaption)."""
    # Root document doesn't have siblings in the same way
    if container.name in ("[document]", None):
        return False
    
    # Check next sibling (existing behavior)
    sibling = container.find_next_sibling()
    if sibling is not None and sibling.name in ("p", "figcaption"):
        if attr_regex.search(sibling.get_text(" ", strip=True)):
            return True
    
    # Check for existing figcaption INSIDE the container (e.g., <figure><figcaption>...</figcaption></figure>)
    if container.name == "figure":
        figcaption = container.find("figcaption")
        if figcaption and attr_regex.search(figcaption.get_text(" ", strip=True)):
            return True
    
    # Also check if container is an <a> or <div> wrapping an <img> with a sibling figcaption
    for child in container.find_all(["img", "figure"], recursive=False):
        if child.name == "figure":
            fc = child.find("figcaption")
            if fc and attr_regex.search(fc.get_text(" ", strip=True)):
                return True
    
    return False


def insert_attribution(container: Tag, attr_html: str) -> None:
    """Insert attribution HTML immediately after container."""
    new_el = BeautifulSoup(attr_html, "html.parser")
    # If container is the root soup (document), append to body instead
    if container.name == "[document]" or container.name is None:
        body = new_el.find("body") if new_el.find("body") else new_el
        if hasattr(container, "body") and container.body:
            container.body.append(new_el)
        else:
            container.append(new_el)
    else:
        container.insert_after(new_el)


# ---------------------------------------------------------------------------
# Core Passes (each runs on a fresh soup but we chain them efficiently)
# ---------------------------------------------------------------------------

def remove_monetization(html: str) -> str:
    """Pass 1: Strip monetization funnels and empty containers."""
    soup = BeautifulSoup(html, "html.parser")
    to_remove: list[Tag] = []

    # 1. <a> tags with monetization domains in href
    for a in list(soup.find_all("a", href=True)):
        if MONETIZATION_DOMAIN_RE.search(a.get("href", "")):
            to_remove.append(a)

    # 2. <a>, <button>, <p>, <div> with monetization text
    for tag in list(soup.find_all(["a", "button", "p", "div"])):
        if tag in to_remove:
            continue
        if tag_has_monetization_text(tag):
            to_remove.append(tag)

    # Remove marked tags
    for tag in to_remove:
        tag.decompose()

    # 2.5. Preserve Google Maps iframes - ensure they're not stripped by empty container removal
    for iframe in soup.find_all("iframe"):
        src = iframe.get("src", "")
        if "google.com/maps" in src:
            # Mark parent containers as non-empty by adding a data attribute
            parent = iframe.parent
            if parent:
                parent["data-preserve-map"] = "true"

    # 3. Iteratively remove empty containers
    changed = True
    while changed:
        changed = False
        for container in list(soup.find_all(EMPTY_CONTAINER_TAGS)):
            if not is_empty_container(container):
                continue
            # Extra safety: don't remove containers with Google Maps iframes
            if container.get("data-preserve-map") == "true":
                continue
            container.decompose()
            changed = True
            break

    return str(soup)


def add_wikimedia_attributions(html: str) -> str:
    """Pass 2: Add CC BY-SA attribution to Wikimedia Commons images."""
    soup = BeautifulSoup(html, "html.parser")

    for img in list(soup.find_all("img", src=True)):
        src = img.get("src", "")
        if not WIKIMEDIA_IMG_RE.search(src):
            continue

        # Determine container: parent if it's a wrapper (<a>, <figure>, <div>), else img itself
        parent = img.parent
        if parent is None or parent.name in ("body", "html", "[document]"):
            container = img
        else:
            container = parent

        if already_attributed(container, ATTRIBUTION_RE):
            continue

        insert_attribution(container, WIKIMEDIA_ATTR_HTML)

    return str(soup)


def add_unsplash_attributions(html: str) -> str:
    """Pass 3: Add Unsplash attribution to Unsplash images."""
    soup = BeautifulSoup(html, "html.parser")

    for img in list(soup.find_all("img", src=True)):
        src = img.get("src", "")
        if not UNSPLASH_IMG_RE.search(src):
            continue

        # Determine container (same logic as Wikimedia)
        parent = img.parent
        if parent is None or parent.name in ("body", "html", "[document]"):
            container = img
        else:
            container = parent

        if already_attributed(container, re.compile(r"unsplash", re.IGNORECASE)):
            continue

        # Create attribution matching the figcaption format from image_curator
        attr_html = (
            '<figcaption style="font-size: 11px; color: #777; text-align: center;">'
            'Image: <a href="https://unsplash.com">Unsplash</a> / Unsplash</figcaption>'
        )
        insert_attribution(container, attr_html)

    return str(soup)


# ---------------------------------------------------------------------------
# Master Pipeline
# ---------------------------------------------------------------------------

def enforce_adsense_compliance(html_content: str) -> str:
    """
    Master enforcement function. Runs all compliance passes in order:
    1. Remove monetization funnels + empty containers
    2. Add Wikimedia Commons attributions
    3. Add Unsplash attributions
    4. Apply existing sanitize_post_html (headings + external links)
    
    Returns sanitized HTML string. Never raises; on error returns original.
    """
    if not html_content or not isinstance(html_content, str):
        return html_content

    try:
        # Pass 1: Monetization removal
        html_content = remove_monetization(html_content)
        
        # Pass 2: Wikimedia attributions
        html_content = add_wikimedia_attributions(html_content)
        
        # Pass 3: Unsplash attributions
        html_content = add_unsplash_attributions(html_content)
        
        # Pass 4: Existing sanitization (headings + external links)
        html_content = sanitize_post_html(html_content)
        
        return html_content
    except Exception:
        # Fail-safe: return original HTML if any pass crashes
        return html_content


# ---------------------------------------------------------------------------
# Optional: Post-level stats for logging/debugging
# ---------------------------------------------------------------------------

def get_compliance_stats(html_before: str, html_after: str) -> dict:
    """Compare before/after and return stats (for logging)."""
    soup_before = BeautifulSoup(html_before, "html.parser")
    soup_after = BeautifulSoup(html_after, "html.parser")
    
    stats = {
        "monetization_links_removed": 0,
        "wikimedia_attributions_added": 0,
        "unsplash_attributions_added": 0,
        "headings_fixed": 0,
        "external_links_hardened": 0,
    }
    
    # Count monetization links removed
    before_mon = soup_before.find_all("a", href=MONETIZATION_DOMAIN_RE)
    after_mon = soup_after.find_all("a", href=MONETIZATION_DOMAIN_RE)
    stats["monetization_links_removed"] = len(before_mon) - len(after_mon)
    
    # Count Wikimedia attributions added
    before_wm_attr = len(soup_before.find_all("p", string=ATTRIBUTION_RE))
    after_wm_attr = len(soup_after.find_all("p", string=ATTRIBUTION_RE))
    stats["wikimedia_attributions_added"] = max(0, after_wm_attr - before_wm_attr)
    
    # Count Unsplash attributions added
    before_us_attr = len([p for p in soup_before.find_all("p") if "image source: unsplash" in p.get_text().lower()])
    after_us_attr = len([p for p in soup_after.find_all("p") if "image source: unsplash" in p.get_text().lower()])
    stats["unsplash_attributions_added"] = max(0, after_us_attr - before_us_attr)
    
    return stats


if __name__ == "__main__":
    # Quick self-test
    test_html = '''
    <h1>Test</h1>
    <p><a href="https://patreon.com/test">Support me</a></p>
    <img src="https://upload.wikimedia.org/test.jpg" alt="test">
    <img src="https://images.unsplash.com/test.jpg" alt="test2">
    <a href="https://example.com">External</a>
    '''
    result = enforce_adsense_compliance(test_html)
    print("=== INPUT ===")
    print(test_html)
    print("\n=== OUTPUT ===")
    print(result)
