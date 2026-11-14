#!/usr/bin/env python3
"""
regex_html_audit.py

Deep HTML error audit for all 168 Blogger posts using regex and BeautifulSoup.
Reads audit_v2_posts_snapshot.json and generates REGEX_ERROR_REPORT.md.

Checks:
1. Empty Anchor Text: <a> tags with no visible text content.
2. Hardcoded HTTP Links: Links using http:// (not https://).
3. Invalid Nested Paragraphs: <p> nested inside <p> (invalid HTML).
4. Excess Line Breaks: 3+ consecutive <br> tags.
5. Empty Headings: <h1>, <h2>, or <h3> tags with no text content.
"""

import re
import sys
import json
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
DEFAULT_SNAPSHOT = ROOT / "content" / "image_audit_20261020" / "audit_v2_posts_snapshot.json"
OUTPUT_REPORT = ROOT / "REGEX_ERROR_REPORT.md"

INTERNAL_HTTP_PATTERNS = [
    re.compile(r"^http://(?:[^/]*\.)?bp\.blogspot\.com", re.I),
    re.compile(r"^http://(?:[^/]*\.)?blogger\.com", re.I),
    re.compile(r"^http://(?:[^/]*\.)?blogspot\.com", re.I),
    re.compile(r"^http://(?:[^/]*\.)?googleusercontent\.com", re.I),
]

# Match 3 or more consecutive <br> tags (optional whitespace and / between)
RE_EXCESS_BR = re.compile(
    r"(?:(?:<br\s*/?>)\s*){3,}",
    re.I
)

# Match hardcoded http:// links in href/src attributes
RE_HTTP_HREF = re.compile(
    r'(?:href|src)\s*=\s*["\']?(http://[^"\'>\s]+)',
    re.I
)

# Match empty heading tags (optional whitespace inside)
RE_EMPTY_HEADING = re.compile(
    r"<(h[123])\s*>\s*</\1\s*>",
    re.I
)


def is_internal_http(url: str) -> bool:
    """Return True if the HTTP URL is an internal Blogger/Google CDN."""
    for pattern in INTERNAL_HTTP_PATTERNS:
        if pattern.search(url):
            return True
    return False


def truncate_context(text: str, max_len: int = 120) -> str:
    """Trim context strings for clean report output."""
    text = " ".join(text.split())
    if len(text) > max_len:
        return text[:max_len].rstrip() + " …"
    return text


def check_empty_anchors(content: str, soup: BeautifulSoup) -> list:
    """Find <a> tags with no visible text (empty or whitespace-only content)."""
    issues = []
    for a in soup.find_all("a"):
        href = a.get("href", "").strip()
        if not href:
            continue
        inner_text = a.get_text(strip=True)
        # Also check for img-only anchors (img without alt acts as empty text)
        has_visible_image = bool(a.find("img") and a.find("img").get("alt", "").strip())
        if not inner_text and not has_visible_image:
            tag_snippet = truncate_context(str(a), 100)
            issues.append({"check": "Empty Anchor Text", "context": tag_snippet})
    return issues


def check_http_links(content: str, soup: BeautifulSoup) -> list:
    """Find href/src attributes using http:// instead of https://."""
    issues = []
    seen = set()
    for match in RE_HTTP_HREF.finditer(content):
        url = match.group(1).rstrip("\"' ")
        if url in seen:
            continue
        seen.add(url)
        if is_internal_http(url):
            continue
        display = url if len(url) <= 100 else url[:97] + "…"
        issues.append({"check": "Hardcoded HTTP Link", "context": display})
    return issues


def check_nested_paragraphs(content: str, soup: BeautifulSoup) -> list:
    """Find <p> tags nested inside other <p> tags."""
    issues = []
    for outer_p in soup.find_all("p"):
        inner_ps = outer_p.find_all("p")
        if inner_ps:
            outer_text = outer_p.get_text(strip=True)
            context = truncate_context(outer_text, 100)
            issues.append({
                "check": "Invalid Nested Paragraph",
                "context": f"Outer `<p>` contains {len(inner_ps)} nested `<p>` tag(s): \"{context}\""
            })
    return issues


def check_excess_line_breaks(content: str, soup: BeautifulSoup) -> list:
    """Find 3 or more consecutive <br> tags."""
    issues = []
    seen_positions = set()
    for match in RE_EXCESS_BR.finditer(content):
        pos = match.start()
        # Bucket nearby matches together so we don't double-count per block
        bucket = pos // 200
        if bucket in seen_positions:
            continue
        seen_positions.add(bucket)
        br_count = len(re.findall(r"<br\s*/?>", match.group(0), re.I))
        # Grab surrounding context from raw HTML for clarity
        snippet_start = max(0, pos - 30)
        snippet_end = min(len(content), pos + 80)
        raw_ctx = content[snippet_start:snippet_end]
        context = truncate_context(raw_ctx, 120)
        issues.append({
            "check": "Excess Line Breaks",
            "context": f"{br_count} consecutive `<br>` tags at: `{context}`"
        })
    return issues


def check_empty_headings(content: str, soup: BeautifulSoup) -> list:
    """Find <h1>, <h2>, or <h3> tags with no text content."""
    issues = []
    for h in soup.find_all(["h1", "h2", "h3"]):
        text = h.get_text(strip=True)
        if not text:
            tag_snippet = truncate_context(str(h), 100)
            issues.append({
                "check": "Empty Heading",
                "context": f"Empty `<{h.name}>` tag: `{tag_snippet}`"
            })
    return issues


def audit_post(post: dict) -> dict:
    """Run all 5 audits on a single post. Returns structured result."""
    pid = str(post.get("id", "unknown"))
    title = " ".join(post.get("title", "Untitled").split())
    url = post.get("url", "")
    content = post.get("content", "")

    if not content:
        return {
            "id": pid, "title": title, "url": url,
            "issues": [], "total": 0
        }

    soup = BeautifulSoup(content, "html.parser")

    all_issues = []
    all_issues.extend(check_empty_anchors(content, soup))
    all_issues.extend(check_http_links(content, soup))
    all_issues.extend(check_nested_paragraphs(content, soup))
    all_issues.extend(check_excess_line_breaks(content, soup))
    all_issues.extend(check_empty_headings(content, soup))

    return {
        "id": pid,
        "title": title,
        "url": url,
        "issues": all_issues,
        "total": len(all_issues),
    }


def generate_report(results: list, report_path: Path) -> None:
    """Write the markdown report to disk."""
    total_posts = len(results)
    flagged_results = [r for r in results if r["total"] > 0]
    clean_results = [r for r in results if r["total"] == 0]

    total_issues = sum(r["total"] for r in results)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Category aggregation
    category_counts = {
        "Empty Anchor Text": 0,
        "Hardcoded HTTP Link": 0,
        "Invalid Nested Paragraph": 0,
        "Excess Line Breaks": 0,
        "Empty Heading": 0,
    }
    posts_with_category = {k: 0 for k in category_counts}

    for r in results:
        seen_cats = set()
        for issue in r["issues"]:
            cat = issue["check"]
            category_counts[cat] = category_counts.get(cat, 0) + 1
            if cat not in seen_cats:
                posts_with_category[cat] = posts_with_category.get(cat, 0) + 1
                seen_cats.add(cat)

    md = []
    md.append("# Deep Regex HTML Audit Report\n")
    md.append(f"**Generated:** {generated_at}  ")
    md.append(f"**Total Posts Analyzed:** {total_posts}  ")
    md.append(f"**Source:** `audit_v2_posts_snapshot.json`\n")

    md.append("## 1. Executive Summary\n")
    md.append("| Metric | Count |")
    md.append("| :--- | :--- |")
    md.append(f"| **Total Posts Analyzed** | `{total_posts}` |")
    md.append(f"| **Posts With Issues** | `{len(flagged_results)}` |")
    md.append(f"| **Clean Posts** | `{len(clean_results)}` |")
    md.append(f"| **Total Issues Found** | `{total_issues}` |\n")

    md.append("### Issues by Category\n")
    md.append("| Check | Total Issues | Affected Posts | Priority |")
    md.append("| :--- | :--- | :--- | :--- |")
    priorities = {
        "Invalid Nested Paragraph": "🔴 Critical",
        "Empty Heading": "🔴 Critical",
        "Hardcoded HTTP Link": "🟠 High",
        "Empty Anchor Text": "🟡 Medium",
        "Excess Line Breaks": "🟢 Low",
    }
    for cat, priority in priorities.items():
        md.append(
            f"| **{cat}** | `{category_counts.get(cat, 0)}` | "
            f"`{posts_with_category.get(cat, 0)}` | {priority} |"
        )
    md.append("")

    md.append("## 2. Recommendations\n")
    md.append("### Invalid Nested Paragraphs (🔴 Critical)")
    md.append("Block-level elements (`<p>`) cannot be nested inside other block-level elements per the HTML5 spec. "
              "Browsers auto-close the outer `<p>` before the inner one, breaking layout. "
              "Replace inner `<p>` tags with `<span>` or restructure the content block.\n")
    md.append("### Empty Headings (🔴 Critical)")
    md.append("Empty heading tags (`<h1>`/`<h2>`/`<h3>`) appear in the DOM, "
              "are indexed by search engines as meaningless signals, and cause screen reader confusion. "
              "Remove or populate them with descriptive text.\n")
    md.append("### Hardcoded HTTP Links (🟠 High)")
    md.append("HTTP links trigger mixed-content warnings on HTTPS pages, reducing trust and potentially being "
              "blocked by browsers. Upgrade all `http://` to `https://` or use protocol-relative `//` where needed.\n")
    md.append("### Empty Anchor Text (🟡 Medium)")
    md.append("Links with no anchor text are invisible to sighted users and meaningless to search engines. "
              "Either remove the `<a>` tag or add descriptive anchor text. "
              "If the link wraps an image, ensure the image has a descriptive `alt` attribute.\n")
    md.append("### Excess Line Breaks (🟢 Low)")
    md.append("Three or more consecutive `<br>` tags are a code smell indicating vertical spacing is "
              "applied with line breaks instead of CSS margins. Replace with CSS `margin-top`/`padding-top` "
              "on the adjacent block element.\n")

    md.append("## 3. Detailed Findings by Post\n")

    # Sort by number of issues descending
    sorted_results = sorted(flagged_results, key=lambda x: x["total"], reverse=True)

    for idx, r in enumerate(sorted_results, 1):
        md.append(f"### {idx}. {r['title']}")
        md.append(f"- **URL:** [{r['url']}]({r['url']})")
        md.append(f"- **Post ID:** `{r['id']}` | **Total Issues:** `{r['total']}`")

        # Group by category
        by_cat: dict[str, list] = {}
        for issue in r["issues"]:
            by_cat.setdefault(issue["check"], []).append(issue["context"])

        for cat, contexts in by_cat.items():
            md.append(f"- **{cat}** ({len(contexts)} issue(s)):")
            for ctx in contexts:
                md.append(f"  - `{ctx}`")
        md.append("")

    if clean_results:
        md.append(f"## 4. Clean Posts ({len(clean_results)} total — no issues found)\n")
        for r in sorted(clean_results, key=lambda x: x["title"]):
            md.append(f"- [{r['title']}]({r['url']}) — `{r['id']}`")
        md.append("")

    report_path.write_text("\n".join(md), encoding="utf-8")
    print(f"\n[SUCCESS] Report written to: {report_path.resolve()}")


def main():
    snap_path = DEFAULT_SNAPSHOT
    if not snap_path.exists():
        print(f"[ERROR] Snapshot not found: {snap_path}", file=sys.stderr)
        sys.exit(1)

    print(f"[INIT] Loading snapshot: {snap_path}")
    with open(snap_path, "r", encoding="utf-8") as f:
        posts = json.load(f)

    print(f"[ANALYSIS] Auditing {len(posts)} posts for 5 HTML error patterns...\n")

    results = []
    for i, p in enumerate(posts, 1):
        result = audit_post(p)
        results.append(result)
        if i % 40 == 0 or i == len(posts):
            print(f"  Progress: {i}/{len(posts)} posts scanned...")

    # Summary stats
    flagged = [r for r in results if r["total"] > 0]
    total_issues = sum(r["total"] for r in results)

    print("\n================ REGEX AUDIT SUMMARY ================")
    print(f"  Posts Scanned:        {len(results)}")
    print(f"  Posts With Issues:    {len(flagged)}")
    print(f"  Clean Posts:          {len(results) - len(flagged)}")
    print(f"  Total Issues Found:   {total_issues}")
    print("======================================================")

    generate_report(results, OUTPUT_REPORT)


if __name__ == "__main__":
    main()
