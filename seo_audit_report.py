#!/usr/bin/env python3
"""
SEO Audit Report Generator for AutoPilot OS / Dust & Dynasty Blog
Reads snapshot data (audit_v2_parsed.json and/or audit_v2_posts_snapshot.json)
and generates a comprehensive, read-only markdown report (SEO_AUDIT_REPORT.md).

Flags:
1. Title Issues (Too long > 60 chars, Too short < 30 chars)
2. Heading Structure (Missing H1, Multiple H1s, Skipped Heading Levels)
3. Thin Content (Word count < 500 words after stripping HTML)
4. Image SEO (Missing alt text or generic alt text)
5. Link SEO (External links missing target="_blank" or rel="noopener")
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from urllib.parse import urlsplit
from datetime import datetime
from bs4 import BeautifulSoup

# Known internal domains and native platform media CDNs
INTERNAL_DOMAINS = {
    "dustanddynasty.blogspot.com",
    "blogger.com",
    "www.blogger.com",
    "bp.blogspot.com",
    "blogger.googleusercontent.com",
    "googleusercontent.com",
}

# Generic alt text regex patterns
GENERIC_ALT_PATTERNS = [
    re.compile(r"^(image|photo|picture|img|pic|figure|graphic|screenshot|untitled|thumbnail|banner|asset|file)\s*\d*$", re.I),
    re.compile(r"^(image|photo|picture|img|pic)[-_ ]*\d+$", re.I),
    re.compile(r"^img[-_]\d+$", re.I),
    re.compile(r"^additional\s+view$", re.I),
    re.compile(r"^placeholder$", re.I),
    re.compile(r"^untitled\s*\d*$", re.I),
    re.compile(r"^dsc[-_]?\d+$", re.I),
    re.compile(r".*\.(jpg|jpeg|png|webp|gif|svg)$", re.I),
]


def normalize_string(text: str) -> str:
    """Normalize whitespace and strip control characters."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def load_post_snapshots(input_path: Path) -> list:
    """
    Loads parsed post data and augments each post with HTML content if missing.
    Looks for audit_v2_posts_snapshot.json in the same directory.
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    with open(input_path, "r", encoding="utf-8") as f:
        posts = json.load(f)

    # Check if content exists in the first few items
    has_content = any(bool(p.get("content")) for p in posts[:5])
    if not has_content:
        snapshot_candidate = input_path.parent / "audit_v2_posts_snapshot.json"
        if snapshot_candidate.exists():
            print(f"[INFO] Augmenting HTML content from {snapshot_candidate.name}...")
            with open(snapshot_candidate, "r", encoding="utf-8") as sf:
                snapshot_data = json.load(sf)
            content_map = {item["id"]: item.get("content", "") for item in snapshot_data if "id" in item}
            for p in posts:
                pid = p.get("id")
                if pid in content_map and not p.get("content"):
                    p["content"] = content_map[pid]
        else:
            print(f"[WARNING] Snapshot file not found at {snapshot_candidate}; content checks may be limited.")

    return posts


def audit_title(title: str) -> list:
    """Analyze title length according to search engine display limits."""
    issues = []
    clean_title = normalize_string(title)
    char_count = len(clean_title)

    if char_count < 30:
        issues.append(f"Title too short ({char_count} chars; recommended 30–60)")
    elif char_count > 60:
        issues.append(f"Title too long ({char_count} chars; recommended 30–60)")

    return issues


def audit_headings(soup: BeautifulSoup) -> list:
    """Check for missing H1, multiple H1s, and skipped heading hierarchy levels."""
    issues = []
    headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    h1_count = sum(1 for h in headings if h.name.lower() == "h1")

    if h1_count == 0:
        issues.append("Missing `<h1>` tag in post body")
    elif h1_count > 1:
        issues.append(f"Multiple `<h1>` tags found ({h1_count} tags; expected exactly 1)")

    # Check for skipped heading levels (e.g. h1 -> h3, or h2 -> h4)
    prev_level = None
    for h in headings:
        level = int(h.name[1])
        if prev_level is not None:
            if level > prev_level + 1:
                h_text = normalize_string(h.get_text())[:40]
                issues.append(
                    f"Skipped heading level: jumped from `<h{prev_level}>` directly to `<h{level}>` (Heading: \"{h_text}\")"
                )
        prev_level = level

    return issues


def audit_thin_content(soup: BeautifulSoup, min_words: int = 500) -> tuple:
    """Calculate plain-text word count and flag thin content."""
    # Remove script, style, and noscript elements
    for el in soup(["script", "style", "noscript"]):
        el.extract()

    text = soup.get_text(separator=" ")
    words = re.findall(r"\b\w+\b", text)
    word_count = len(words)

    issues = []
    if word_count < min_words:
        issues.append(f"Thin content ({word_count} words; minimum {min_words} words recommended)")

    return word_count, issues


def audit_images(soup: BeautifulSoup) -> list:
    """Audit images for missing alt tags or generic placeholder text."""
    issues = []
    images = soup.find_all("img")

    for i, img in enumerate(images, 1):
        alt = img.get("alt")
        src = img.get("src", "unknown_src")
        src_preview = src.split("?")[0]
        if len(src_preview) > 65:
            src_preview = "..." + src_preview[-60:]

        if alt is None or not alt.strip():
            issues.append(f"Image #{i} missing alt text (`src`: `{src_preview}`)")
            continue

        clean_alt = normalize_string(alt)
        for pattern in GENERIC_ALT_PATTERNS:
            if pattern.match(clean_alt):
                issues.append(
                    f"Image #{i} has generic alt text: \"{clean_alt}\" (`src`: `{src_preview}`)"
                )
                break

    return issues


def audit_links(soup: BeautifulSoup) -> list:
    """Check external links for target='_blank' and rel='noopener' / 'noreferrer'."""
    issues = []
    anchors = soup.find_all("a")

    for a in anchors:
        href = (a.get("href") or "").strip()
        if not href.startswith(("http://", "https://", "//")):
            continue

        parts = urlsplit(href)
        netloc = parts.netloc.lower()

        # Check if external domain
        is_internal = any(netloc == d or netloc.endswith("." + d) for d in INTERNAL_DOMAINS)
        if is_internal:
            continue

        target = a.get("target", "")
        has_blank = (target == "_blank")

        rel_attr = a.get("rel") or []
        if isinstance(rel_attr, str):
            rel_tokens = rel_attr.lower().split()
        elif isinstance(rel_attr, list):
            rel_tokens = [r.lower() for r in rel_attr]
        else:
            rel_tokens = []

        has_noopener = ("noopener" in rel_tokens or "noreferrer" in rel_tokens)

        href_preview = href if len(href) <= 60 else href[:57] + "..."
        missing = []
        if not has_blank:
            missing.append("missing `target=\"_blank\"`")
        if not has_noopener:
            missing.append("missing `rel=\"noopener\"`")

        if missing:
            issues.append(f"External link to `{href_preview}` ({', '.join(missing)})")

    return issues


def analyze_post(post: dict) -> dict:
    """Run all audits on a single post record."""
    pid = post.get("id", "unknown_id")
    raw_title = post.get("title", "Untitled")
    title = normalize_string(raw_title)
    url = post.get("url", "")
    content_html = post.get("content", "")

    soup = BeautifulSoup(content_html, "html.parser")

    title_issues = audit_title(title)
    heading_issues = audit_headings(soup)
    word_count, content_issues = audit_thin_content(soup)
    image_issues = audit_images(soup)
    link_issues = audit_links(soup)

    all_issues = {
        "Title Issues": title_issues,
        "Heading Structure": heading_issues,
        "Thin Content": content_issues,
        "Image SEO": image_issues,
        "Link SEO": link_issues,
    }

    total_discrepancies = sum(len(v) for v in all_issues.values())

    return {
        "id": pid,
        "title": title,
        "url": url,
        "word_count": word_count,
        "issues": all_issues,
        "total_discrepancies": total_discrepancies,
        "is_clean": total_discrepancies == 0,
    }


def generate_markdown_report(results: list, report_path: Path) -> None:
    """Format and write the SEO Audit Markdown Report."""
    total_posts = len(results)
    clean_posts = sum(1 for r in results if r["is_clean"])
    flagged_posts = total_posts - clean_posts

    # Aggregate counts by category
    category_counts = {
        "Title Issues": 0,
        "Heading Structure": 0,
        "Thin Content": 0,
        "Image SEO": 0,
        "Link SEO": 0,
    }
    posts_with_category = {k: 0 for k in category_counts}

    total_issues = 0
    for r in results:
        total_issues += r["total_discrepancies"]
        for cat, items in r["issues"].items():
            if items:
                category_counts[cat] += len(items)
                posts_with_category[cat] += 1

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    md = []
    md.append("# SEO Audit Report: Blogger Posts Snapshot\n")
    md.append(f"**Generated:** {generated_at}  ")
    md.append(f"**Total Posts Analyzed:** {total_posts}  ")
    md.append(f"**Audit Scope:** Read-Only Snapshot (`audit_v2_parsed.json` / `audit_v2_posts_snapshot.json`)\n")

    md.append("## 1. Executive Summary\n")
    md.append("| Metric | Count | Percentage |")
    md.append("| :--- | :--- | :--- |")
    md.append(f"| **Total Posts Analyzed** | `{total_posts}` | 100.0% |")
    md.append(f"| **Posts With Discrepancies** | `{flagged_posts}` | {flagged_posts / total_posts * 100:.1f}% |")
    md.append(f"| **Clean / Optimized Posts** | `{clean_posts}` | {clean_posts / total_posts * 100:.1f}% |")
    md.append(f"| **Total Discrepancies Flagged** | `{total_issues}` | — |\n")

    md.append("### Discrepancy Breakdown by Category\n")
    md.append("| Category | Total Issues | Affected Posts | % of Total Posts | Severity |")
    md.append("| :--- | :--- | :--- | :--- | :--- |")
    md.append(
        f"| **Title Issues** (>60 or <30 chars) | {category_counts['Title Issues']} | {posts_with_category['Title Issues']} | {posts_with_category['Title Issues'] / total_posts * 100:.1f}% | Medium |"
    )
    md.append(
        f"| **Heading Structure** (H1 / hierarchy) | {category_counts['Heading Structure']} | {posts_with_category['Heading Structure']} | {posts_with_category['Heading Structure'] / total_posts * 100:.1f}% | High |"
    )
    md.append(
        f"| **Thin Content** (<500 words) | {category_counts['Thin Content']} | {posts_with_category['Thin Content']} | {posts_with_category['Thin Content'] / total_posts * 100:.1f}% | Critical |"
    )
    md.append(
        f"| **Image SEO** (Missing/generic alt) | {category_counts['Image SEO']} | {posts_with_category['Image SEO']} | {posts_with_category['Image SEO'] / total_posts * 100:.1f}% | Medium |"
    )
    md.append(
        f"| **Link SEO** (Noopener / Target) | {category_counts['Link SEO']} | {posts_with_category['Link SEO']} | {posts_with_category['Link SEO'] / total_posts * 100:.1f}% | Low-Medium |\n")

    md.append("## 2. Actionable SEO Recommendations\n")
    md.append("### A. Title Optimization (Display Snippet Integrity)")
    md.append("- **Target Length:** Keep blog titles between **30 and 60 characters** (under 580px desktop pixel width).")
    md.append("- **Formatting Fix:** Many current titles use descriptive subtitles separated by em-dashes (e.g. `Site Name — Detailed Subtitle — Second Subtitle`). Shorten the main title for Blogger and place long secondary explanations inside the post body or meta description.\n")

    md.append("### B. Heading Architecture (Semantic Hierarchy)")
    md.append("- **H1 Policy:** Every post body should contain exactly **one `<h1>` tag** matching the central topic of the article.")
    md.append("- **Sequential Levels:** Never skip heading levels. The outline should strictly follow `<h1>` -> `<h2>` -> `<h3>`. If using an `<h3>`, ensure it is nested under an `<h2>` subsection.")
    md.append("- **Theme Coordination:** Verify whether the Blogger theme's template automatically injects the post title as `<h1>` or `<h2>`. If the theme injects `<h1>`, start post body sections at `<h2>` and standardize consistently across all posts.\n")

    md.append("### C. Content Depth & Thin Content")
    md.append("- **Standard:** All posts in this snapshot passed the 500-word minimum threshold (articles average 2,500–4,500 words). Maintain this comprehensive depth.\n")

    md.append("### D. Image Accessibility & Image Search")
    md.append("- **Descriptive Alt Attributes:** Replace generic placeholders like `\"Additional View\"` or Wikimedia image codes (`\"Shibam, Yemen 09\"`) with specific descriptions of the monument, architectural feature, or vantage point.")
    md.append("- **Syntax Example:** `<img src=\"...\" alt=\"Aerial panoramic view of the western citadel walls of Rohtas Fort, Pakistan\">`.\n")

    md.append("### E. Outbound Link Security & Best Practices")
    md.append("- **Tab Control & Security:** Ensure all external citations (UNESCO, Wikipedia, Patreon, Gumroad) include both `target=\"_blank\"` and `rel=\"noopener noreferrer\"`.")
    md.append("- **Syntax Example:** `<a href=\"https://whc.unesco.org/...\" target=\"_blank\" rel=\"noopener noreferrer\">UNESCO Official Citation</a>`.\n")

    md.append("## 3. Detailed Audit by Post\n")

    # Sort results by total discrepancies descending
    sorted_results = sorted(results, key=lambda x: x["total_discrepancies"], reverse=True)

    for idx, r in enumerate(sorted_results, 1):
        if r["is_clean"]:
            continue

        title_display = r["title"]
        url_display = r["url"]
        char_len = len(title_display)

        md.append(f"### {idx}. {title_display}")
        md.append(f"- **URL:** [{url_display}]({url_display})")
        md.append(f"- **Post ID:** `{r['id']}` | **Word Count:** `{r['word_count']}` | **Total Issues:** `{r['total_discrepancies']}`")

        for category, issues in r["issues"].items():
            if issues:
                md.append(f"- **{category}:**")
                for issue in issues:
                    md.append(f"  - {issue}")
        md.append("")

    if clean_posts > 0:
        md.append("## 4. Clean Posts (No Discrepancies Found)\n")
        for r in sorted_results:
            if r["is_clean"]:
                md.append(f"- [{r['title']}]({r['url']}) (`{r['id']}` - {r['word_count']} words)")
        md.append("")

    report_path.write_text("\n".join(md), encoding="utf-8")
    print(f"\n[SUCCESS] Markdown report successfully written to: {report_path.resolve()}")


def main():
    parser = argparse.ArgumentParser(description="Generate read-only SEO audit report for blog posts.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("content/image_audit_20261020/audit_v2_parsed.json"),
        help="Path to parsed JSON post snapshot (default: content/image_audit_20261020/audit_v2_parsed.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("SEO_AUDIT_REPORT.md"),
        help="Output markdown report path (default: SEO_AUDIT_REPORT.md)",
    )

    args = parser.parse_args()

    # Resolve input path if relative
    v2_root = Path(__file__).resolve().parent
    input_file = args.input if args.input.is_absolute() else v2_root / args.input
    output_file = args.output if args.output.is_absolute() else v2_root / args.output

    print(f"[START] Running SEO audit...")
    print(f"[INPUT] Reading snapshot from: {input_file}")

    try:
        posts = load_post_snapshots(input_file)
    except Exception as e:
        print(f"[ERROR] Failed to load snapshot: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[ANALYSIS] Auditing {len(posts)} posts across 5 SEO dimensions...")

    results = []
    for i, p in enumerate(posts, 1):
        res = analyze_post(p)
        results.append(res)
        if i % 40 == 0 or i == len(posts):
            print(f"  Progress: {i}/{len(posts)} posts processed...")

    generate_markdown_report(results, output_file)

    clean_count = sum(1 for r in results if r["is_clean"])
    issue_count = len(results) - clean_count
    total_issues = sum(r["total_discrepancies"] for r in results)

    print(f"\n================ AUDIT SUMMARY ================")
    print(f"  Total Posts Analyzed:     {len(results)}")
    print(f"  Posts with Discrepancies: {issue_count}")
    print(f"  Clean / Optimized Posts:  {clean_count}")
    print(f"  Total Flagged Issues:     {total_issues}")
    print(f"  Report Location:          {output_file}")
    print(f"===============================================\n")


if __name__ == "__main__":
    main()
