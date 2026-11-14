
"""
audit_content.py

Audits Blogger posts for basic content-quality and SEO signals.

Requirements:
    pip install beautifulsoup4

Expected project structure:
    D:\\Projects\\AutoPilot_OS_v2\\
        audit_content.py
        blogger_client.py
        reports\\

Run:
    python audit_content.py

Note:
    This is a heuristic audit, not a definitive measure of content quality
    or a prediction of Google AdSense approval.
"""

import csv
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from blogger_client import list_posts


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent
REPORTS_DIR = PROJECT_DIR / "reports"

BLOG_DOMAIN = "dustanddynasty.blogspot.com"

AI_FLUFF_PHRASES = [
    "delve",
    "tapestry",
    "testament",
    "furthermore",
    "moreover",
    "in conclusion",
    "it is important to note",
    "rich history",
    "hidden gem",
]

CSV_COLUMNS = [
    "id",
    "title",
    "url",
    "words",
    "images",
    "ext_links",
    "score",
    "issues",
]


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def clean_text(html):
    """Convert HTML into readable plain text."""
    if not html:
        return ""

    try:
        soup = BeautifulSoup(html, "html.parser")

        # Remove elements that normally do not contain article text.
        for element in soup(["script", "style", "noscript", "template"]):
            element.decompose()

        return soup.get_text(separator=" ", strip=True)

    except Exception as exc:
        print(f"Warning: Could not parse post HTML: {exc}")
        return ""


def count_words(text):
    """Count words while handling punctuation and Unicode text."""
    return len(re.findall(r"\b[\w]+(?:['’\-][\w]+)*\b", text, re.UNICODE))


def count_links(soup):
    """
    Count internal and external HTTP(S) links.

    Internal links contain the configured Blogger domain.
    External links use HTTP(S) and point to another domain.
    Non-HTTP links, such as mailto: and javascript:, are ignored.
    """
    internal_count = 0
    external_count = 0

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()

        if not href:
            continue

        # Accept absolute HTTP(S) links and protocol-relative links.
        if href.startswith("//"):
            href = "https:" + href

        parsed = urlparse(href)

        if parsed.scheme.lower() not in ("http", "https"):
            continue

        hostname = (parsed.hostname or "").lower()

        if not hostname:
            continue

        if BLOG_DOMAIN in hostname:
            internal_count += 1
        else:
            external_count += 1

    return internal_count, external_count


def find_fluff_phrases(text):
    """
    Find configured overused phrases in article text.

    Returns a list of distinct phrases found, not the number of
    times each phrase appears.
    """
    found = []
    normalized_text = text.casefold()

    for phrase in AI_FLUFF_PHRASES:
        pattern = r"(?<!\w)" + re.escape(phrase.casefold()) + r"(?!\w)"

        if re.search(pattern, normalized_text):
            found.append(phrase)

    return found


def analyze_post(post):
    """Analyze one Blogger post and return its audit results."""
    post_id = post.get("id", "")
    title = str(post.get("title") or "Untitled")
    url = str(post.get("url") or "")

    # Handle missing or malformed post content gracefully.
    content = post.get("content") or ""

    if not isinstance(content, str):
        content = str(content)

    try:
        soup = BeautifulSoup(content, "html.parser")

        # Remove non-content elements before counting words.
        for element in soup(["script", "style", "noscript", "template"]):
            element.decompose()

        plain_text = soup.get_text(separator=" ", strip=True)
        words = count_words(plain_text)

        h2_count = len(soup.find_all("h2"))
        h3_count = len(soup.find_all("h3"))
        image_count = len(soup.find_all("img"))

        internal_links, external_links = count_links(soup)
        fluff_phrases = find_fluff_phrases(plain_text)

    except Exception as exc:
        print(f"Warning: Failed to analyze '{title}': {exc}")

        words = 0
        h2_count = 0
        h3_count = 0
        image_count = 0
        internal_links = 0
        external_links = 0
        fluff_phrases = []

    # -----------------------------------------------------
    # Scoring: start at 100 and apply configured deductions.
    # -----------------------------------------------------

    score = 100
    issues = []

    if words < 500:
        score -= 30
        issues.append(f"Word count below 500 (-30; {words} words)")

    if h2_count + h3_count == 0:
        score -= 15
        issues.append("No H2/H3 headings (-15)")

    if image_count == 0:
        score -= 10
        issues.append("No images (-10)")

    if external_links == 0:
        score -= 20
        issues.append("No external links/citations (-20)")

    if len(fluff_phrases) > 2:
        score -= 25
        phrases = ", ".join(fluff_phrases)
        issues.append(f"More than 2 AI-fluff phrases (-25; found: {phrases})")

    score = max(0, score)

    # Include extra diagnostic information in the issues column
    # without applying additional score deductions.
    if fluff_phrases and len(fluff_phrases) <= 2:
        issues.append("Review possible fluff: " + ", ".join(fluff_phrases))

    if internal_links == 0:
        issues.append("No internal links detected (no score deduction)")

    if not issues:
        issues.append("No configured rule violations detected")

    return {
        "id": post_id,
        "title": title,
        "url": url,
        "words": words,
        "images": image_count,
        "ext_links": external_links,
        "score": score,
        "issues": " | ".join(issues),
        # Additional information is kept internally for terminal output.
        "_h2": h2_count,
        "_h3": h3_count,
        "_internal_links": internal_links,
        "_fluff_phrases": fluff_phrases,
    }


# ---------------------------------------------------------
# Main program
# ---------------------------------------------------------

def main():
    """Fetch posts, audit them, save a CSV report and print a summary."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    report_date = date.today().isoformat()
    report_path = REPORTS_DIR / f"content_audit_{report_date}.csv"

    print("Dust and Dynasty — Content Audit")
    print("=" * 45)
    print("Fetching Blogger posts...")

    try:
        posts = list_posts()

        if posts is None:
            raise ValueError("list_posts() returned None instead of a list.")

        if not isinstance(posts, (list, tuple)):
            raise TypeError("list_posts() must return a list of post dictionaries.")

    except Exception as exc:
        print(f"Error: Could not retrieve Blogger posts: {exc}")
        print("Check blogger_client.py, API credentials and internet access.")
        return

    results = []

    for index, post in enumerate(posts, start=1):
        if not isinstance(post, dict):
            print(f"Warning: Skipping invalid post entry #{index}.")
            continue

        try:
            result = analyze_post(post)
            results.append(result)
            print(f"[{index}/{len(posts)}] Audited: {result['title']}")

        except Exception as exc:
            title = post.get("title", "Unknown") if isinstance(post, dict) else "Unknown"
            print(f"Warning: Could not audit '{title}': {exc}")

    # Lowest score first; title provides a stable secondary ordering.
    results.sort(key=lambda item: (item["score"], item["title"].casefold()))

    try:
        # utf-8-sig helps Excel display titles correctly.
        with report_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS)
            writer.writeheader()

            for result in results:
                writer.writerow({
                    column: result[column]
                    for column in CSV_COLUMNS
                })

    except OSError as exc:
        print(f"\nError: Could not save the CSV report: {exc}")
        return

    # -----------------------------------------------------
    # Summary
    # -----------------------------------------------------

    print("\n" + "=" * 60)
    print("AUDIT SUMMARY")
    print("=" * 60)
    print(f"Posts retrieved: {len(posts)}")
    print(f"Posts successfully audited: {len(results)}")
    print(f"Report saved to: {report_path}")

    if not results:
        print("\nNo valid posts were available to audit.")
        return

    print("\n5 LOWEST-SCORING POSTS")
    print("-" * 60)

    for rank, result in enumerate(results[:5], start=1):
        print(f"\n{rank}. {result['title']}")
        print(f"   Score: {result['score']}/100")
        print(f"   URL:   {result['url'] or '(missing URL)'}")

        if result["issues"]:
            print(f"   Issues: {result['issues']}")

    print("\n" + "-" * 60)
    print("Audit complete.")
    print(
        "Important: These scores measure only the configured rules. "
        "They do not establish actual content quality or predict "
        "Google AdSense approval."
    )


if __name__ == "__main__":
    main()
