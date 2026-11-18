#!/usr/bin/env python3
"""
sanitize_html.py

Reusable HTML sanitization module for AutoPilot OS.
Ensures all generated and published posts adhere to SEO & HTML standards:
1. Heading Hierarchy:
   - Eliminates redundant <h1> tags (converts subsequent <h1> tags to <h2>).
   - Promotes hierarchy-breaking <h3> tags (first heading in body, or immediately
     following an <h1>) to <h2>.
2. Link Security & SEO:
   - Injects target="_blank" on external outbound links.
   - Injects rel="noopener noreferrer" while preserving existing tokens (e.g. nofollow).
   - Ignores internal blog URLs and native Blogger media CDNs.
"""

from urllib.parse import urlsplit
from bs4 import BeautifulSoup

INTERNAL_DOMAINS = {
    "dustanddynasty.blogspot.com",
    "blogger.com",
    "www.blogger.com",
    "bp.blogspot.com",
    "blogger.googleusercontent.com",
    "googleusercontent.com",
}


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


def sanitize_links(html_content: str) -> str:
    """
    Ensures all external links have target="_blank" and rel="noopener noreferrer".
    Preserves existing rel values (such as nofollow).
    """
    if not html_content:
        return html_content

    soup = BeautifulSoup(html_content, "html.parser")
    modified = False

    for a in soup.find_all("a"):
        href = (a.get("href") or "").strip()
        if not is_external_link(href):
            continue

        # 1. Enforce target="_blank"
        if a.get("target") != "_blank":
            a["target"] = "_blank"
            modified = True

        # 2. Enforce rel="noopener noreferrer"
        current_rel = a.get("rel")
        if current_rel is None:
            rel_tokens = []
        elif isinstance(current_rel, str):
            rel_tokens = current_rel.split()
        elif isinstance(current_rel, list):
            rel_tokens = list(current_rel)
        else:
            rel_tokens = []

        existing_lower = [t.lower() for t in rel_tokens]
        added = False
        for required_token in ["noopener", "noreferrer"]:
            if required_token not in existing_lower:
                rel_tokens.append(required_token)
                added = True

        if added or current_rel is None:
            a["rel"] = " ".join(rel_tokens)
            modified = True

    return str(soup) if modified else html_content


def sanitize_headings(html_content: str) -> str:
    """
    Repairs heading hierarchy in HTML content.
    - Converts multiple <h1> tags (after the first) to <h2>.
    - Converts hierarchy-breaking <h3> tags (after <h1> or at start) to <h2>.
    """
    if not html_content:
        return html_content

    soup = BeautifulSoup(html_content, "html.parser")
    headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    if not headings:
        return html_content

    modified = False
    prev_level = None
    h1_seen = False

    for h in headings:
        tag_name = h.name.lower()

        # Rule 1: Convert extra <h1> tags to <h2>
        if tag_name == "h1":
            if h1_seen:
                h.name = "h2"
                tag_name = "h2"
                modified = True
            else:
                h1_seen = True

        # Rule 2: Convert hierarchy-breaking <h3> tags to <h2>
        if tag_name == "h3":
            if prev_level is None or prev_level == 1:
                h.name = "h2"
                tag_name = "h2"
                modified = True

        prev_level = int(tag_name[1])

    return str(soup) if modified else html_content


def sanitize_post_html(html: str) -> str:
    """
    Master sanitization function.
    Applies heading hierarchy normalization followed by external link sanitization.
    """
    if not html:
        return html

    html = sanitize_headings(html)
    html = sanitize_links(html)
    return html


if __name__ == "__main__":
    import sys
    from pathlib import Path

    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
        if target.is_file():
            raw = target.read_text(encoding="utf-8")
            cleaned = sanitize_post_html(raw)
            target.write_text(cleaned, encoding="utf-8")
            print(f"[OK] Sanitized {target}")
        else:
            print(f"[ERROR] File not found: {target}")
    else:
        print("Usage: python sanitize_html.py <file.html>")
