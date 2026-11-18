#!/usr/bin/env python3
"""
ai_draft_generator.py - Generate AI draft using FreeLLMAPI with Competitive Research
and Deterministic Quality Scorer with Revision Loop.
"""

import csv
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

# Optional dependency - duckduckgo_search
try:
    from duckduckgo_search import DDGS
    DUCKDUCKGO_AVAILABLE = True
except ImportError:
    DUCKDUCKGO_AVAILABLE = False
    DDGS = None
    print("[WARNING] duckduckgo-search not installed. Competitor research will be skipped.")
    print("         Run: pip install duckduckgo-search")

# Optional dependency - BeautifulSoup for HTML cleaning
try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False
    BeautifulSoup = None

from openai import OpenAI

# FreeLLMAPI endpoint (OpenAI-compatible)
UNIFIED_API_KEY = "freellmapi-1d1a45a24fc0a9e7d626522fe2e89fa95d449e8d7a8cbfa9"
client = OpenAI(
    base_url="http://127.0.0.1:31415/v1",
    api_key=UNIFIED_API_KEY
)

PENDING_DIR = Path(r"D:\Projects\AutoPilot_OS_v2\content\pending")
REMAINING_CSV = Path(r"D:\Projects\AutoPilot_OS_v2\topic_lists\remaining_topics.csv")
SITES_CSV = Path(r"D:\Projects\AutoPilot_OS_v2\sites.csv")
VENV_PYTHON = Path(r"D:\Projects\AutoPilot_OS_v2\os_env\Scripts\python.exe")

# Models to test - FreeLLMAPI serves these models
MODELS_TO_TEST = ["auto", "qwen3.8-max", "glm-5.3", "claude-sonnet-4-5"]

QUALITY_THRESHOLD = 85
MAX_REVISIONS = 1  # One revision = max 2 LLM calls total


def normalize_title(title: str) -> str:
    return unicodedata.normalize('NFC', title.strip().lower())


def find_site_in_master_list(title: str):
    """Search sites.csv for a matching site_name. Returns (title, country, year) or None."""
    if not SITES_CSV.exists():
        return None
    target = normalize_title(title)
    with open(SITES_CSV, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            site_name = row.get('site_name', '')
            if normalize_title(site_name) == target:
                return site_name, row.get('country', ''), row.get('year_inscribed', '')
    return None


def load_next_topic(cli_title: str | None = None):
    """Load topic: CLI arg > first row from remaining_topics.csv."""
    if cli_title:
        found = find_site_in_master_list(cli_title)
        if found:
            return found
        response = input(f"[Topic] '{cli_title}' not found in sites.csv. Use anyway? (y/n): ").strip().lower()
        if response == 'y':
            return cli_title, "", ""
        return None, None, None

    # Primary source: remaining_topics.csv
    if REMAINING_CSV.exists():
        with open(REMAINING_CSV, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                return row.get('master_title', ''), row.get('country', ''), row.get('year_inscribed', '')

    # Fallback: first row from sites.csv
    if SITES_CSV.exists():
        with open(SITES_CSV, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                return row.get('site_name', ''), row.get('country', ''), row.get('year_inscribed', '')

    return None, None, None


def slugify(title):
    """Create URL/filesystem-safe slug from title."""
    text = unicodedata.normalize("NFKD", title)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    text = re.sub(r"-{2,}", "-", text)
    return text[:120] or "draft"


def competitive_research(topic: str) -> str:
    """
    Search DuckDuckGo for competitor article angles.
    Returns a formatted string or empty string on failure.
    """
    if not DUCKDUCKGO_AVAILABLE:
        print("[Research] duckduckgo_search not installed. Skipping competitor research.")
        return ""

    query = f"{topic} UNESCO World Heritage"
    print(f"[Research] Searching DuckDuckGo: {query}")
    
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        
        if not results:
            print("[Research] No results returned.")
            return ""
        
        titles = [r.get('title', '').strip() for r in results if r.get('title')]
        if not titles:
            return ""
        
        competitor_string = "Competitor Article Angles: " + ", ".join(titles[:3])
        print(f"[Research] Found angles: {competitor_string}")
        return competitor_string
        
    except Exception as e:
        print(f"[Research] DuckDuckGo search failed (graceful fallback): {e}")
        return ""


def score_article(html_text: str, primary_keyword: str) -> dict:
    """
    Deterministic Quality Scorer.
    Returns dict with 'score' (0-100) and 'errors' (list of strings).
    """
    score = 100
    errors = []
    
    # Strip HTML tags for text analysis
    text_only = re.sub(r'<[^>]+>', ' ', html_text)
    text_only = re.sub(r'\s+', ' ', text_only).strip()
    words = text_only.split()
    word_count = len(words)
    
    # 1. Word count < 2500: -20 points
    if word_count < 2500:
        score -= 20
        errors.append(f"Word count {word_count} < 2500 (-20)")
    
    # 2. Less than 7 <h2> tags: -15 points
    h2_count = len(re.findall(r'<h2\b', html_text, flags=re.IGNORECASE))
    if h2_count < 7:
        score -= 15
        errors.append(f"Only {h2_count} <h2> tags (need >= 7) (-15)")
    
    # 3. Primary keyword not in first 150 words (case-insensitive): -15 points
    first_150_words = " ".join(words[:150]).lower()
    keyword_lower = primary_keyword.lower()
    # Also check for partial keyword match (e.g., "Omo Valley" in "Lower Valley of the Omo")
    keyword_parts = [part for part in keyword_lower.split() if len(part) > 3]
    keyword_found = keyword_lower in first_150_words
    if not keyword_found and keyword_parts:
        # Check if any significant part of keyword appears
        keyword_found = any(part in first_150_words for part in keyword_parts)
    if not keyword_found:
        score -= 15
        errors.append(f"Primary keyword '{primary_keyword}' not in first 150 words (-15)")
    
    # 4. Missing JSON-LD <script type="application/ld+json">: -20 points
    if 'application/ld+json' not in html_text:
        score -= 20
        errors.append("Missing JSON-LD schema (-20)")
    
    # 5. Missing <!--more--> tag: -10 points
    if '<!--more-->' not in html_text:
        score -= 10
        errors.append("Missing <!--more--> tag (-10)")
    
    # 6. Missing internal link to dustanddynasty.blogspot.com: -10 points
    if 'dustanddynasty.blogspot.com' not in html_text:
        score -= 10
        errors.append("Missing internal link to dustanddynasty.blogspot.com (-10)")
    
    # Clamp score
    score = max(0, score)
    
    return {'score': score, 'errors': errors}


def build_prompt(topic, country, year, competitor_angles, internal_links=None):
    """Build strict prompt enforcing the exact HTML structure."""

    # Build internal links section
    links_section = ""
    if internal_links:
        links_list = "\n".join(
            f'   - <a href="{url}" rel="noopener noreferrer" style="color:#0b5ed7;font-weight:700;text-decoration:underline;text-decoration-color:#0b5ed7;" target="_blank">{title}</a>'
            for title, url in internal_links
        )
        links_section = (
            'INTERNAL LINKING (REQUIRED - embed 2-3 naturally within article body):\n'
            f'{links_list}\n'
            'Naturally embed 2-3 of these internal links within your article body using <a> tags.\n'
            'Do not force links where they do not fit contextually.\n\n'
        )

    # Competitor research section
    competitor_section = ""
    if competitor_angles:
        competitor_section = f"COMPETITOR RESEARCH:\n{competitor_angles}\n\nDifferentiate your angle. Do not copy these titles. Go deeper.\n\n"

    prompt = (
        'You are a professional travel writer for "Dust and Dynasty" \u2014 a UNESCO World Heritage site encyclopedia.\n\n'
        'Write a comprehensive 3000-word article about: ' + topic + ' (' + country + ', inscribed ' + year + ').\n\n'
        + competitor_section +
        'OUTPUT REQUIREMENTS \u2014 FOLLOW EXACTLY:\n\n'
        '1. Start with an SEO-optimized, click-worthy <h1> title (e.g., "The Great Wall of China: A Journey Through Time and Stone").\n'
        '2. Directly underneath the <h1>, add a short, compelling subtitle formatted as: <p><em>{subtitle}</em></p>\n'
        '3. Then a lead paragraph: <p style="font-size: 1.05em; color: #555; font-style: italic; margin-top: 0;">[1-2 sentence poetic summary with location and UNESCO status]</p>\n'
        '4. Then a summary table in this EXACT format:\n'
        '<div style="background: #f8f9fa; border-left: 4px solid #2563eb; padding: 14px 18px; margin: 20px 0; border-radius: 4px;"><table style="border-collapse: collapse; width: 100%;"><tr><td style="padding: 4px 10px 4px 0; vertical-align: top; font-weight: bold; white-space: nowrap;">Location:</td><td style="padding: 4px 0;">[Country, region, coordinates]</td></tr><tr><td style="padding: 4px 10px 4px 0; vertical-align: top; font-weight: bold; white-space: nowrap;">Year of UNESCO Inscription:</td><td style="padding: 4px 0;">' + year + '</td></tr><tr><td style="padding: 4px 10px 4px 0; vertical-align: top; font-weight: bold; white-space: nowrap;">Category:</td><td style="padding: 4px 0;">[Cultural/Natural/Mixed]</td></tr><tr><td style="padding: 4px 10px 4px 0; vertical-align: top; font-weight: bold; white-space: nowrap;">UNESCO Reference:</td><td style="padding: 4px 0;">[Reference number]</td></tr><tr><td style="padding: 4px 10px 4px 0; vertical-align: top; font-weight: bold; white-space: nowrap;">Criteria:</td><td style="padding: 4px 0;">[e.g., (i)(ii)(iv)]</td></tr><tr><td style="padding: 4px 10px 4px 0; vertical-align: top; font-weight: bold; white-space: nowrap;">Coordinates:</td><td style="padding: 4px 0;">[Lat, Long]</td></tr><tr><td style="padding: 4px 10px 4px 0; vertical-align: top; font-weight: bold; white-space: nowrap;">Area:</td><td style="padding: 4px 0;">[Area in hectares/sq km]</td></tr></table></div>\n'
        '5. Then <!--more--> on its own line.\n'
        '6. Then AT LEAST 7 <h2> sections (no inline styles on h2), each with 2-4 <p> paragraphs.\n'
        '   - Use bold for key terms on first mention.\n'
        '   - Include internal links to other posts where relevant: <a href="https://dustanddynasty.blogspot.com/2026/10/..." rel="noopener noreferrer" style="color:#0b5ed7;font-weight:700;text-decoration:underline;text-decoration-color:#0b5ed7;" target="_blank">Linked Post Title</a>\n'
        + links_section +
        '7. REQUIRED SPECIAL SECTIONS (in this order):\n'
        '   <h2>\u2726 Also Read \u2014 [Related Post]</h2>\n'
        '   <p><a href="..." rel="noopener noreferrer" style="color:#0b5ed7;font-weight:700;text-decoration:underline;text-decoration-color:#0b5ed7;" target="_blank">Related Post Title</a></p>\n'
        '   <p>One sentence description.</p>\n\n'
        '   <h2>\u2726 Conclusion</h2>\n'
        '   <p>Final reflective paragraph tying history, significance, and threats.</p>\n'
        '   <p>Call to reflection or action.</p>\n\n'
        '   <h2>\u2726 Frequently Asked Questions</h2>\n'
        '   <p>Question 1?</p>\n'
        '   <p>Answer.</p>\n'
        '   <p>Question 2?</p>\n'
        '   <p>Answer.</p>\n'
        '   (minimum 4 Q&A pairs)\n\n'
        '   <h2>\U0001f9fe Summary Table of Facts</h2>\n'
        '   CRITICAL: For the Summary Table of Facts, you MUST output exactly this HTML structure:\n'
        '   <table style="width: 100%; border-collapse: collapse;">\n'
        '     <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Site Name</strong></td><td style="padding: 8px; border: 1px solid #ddd;">' + topic + '</td></tr>\n'
        '     <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Country</strong></td><td style="padding: 8px; border: 1px solid #ddd;">' + country + '</td></tr>\n'
        '     <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Continent</strong></td><td style="padding: 8px; border: 1px solid #ddd;">[Continent]</td></tr>\n'
        '     <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Category</strong></td><td style="padding: 8px; border: 1px solid #ddd;">[Cultural/Natural/Mixed]</td></tr>\n'
        '     <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Year of Inscription</strong></td><td style="padding: 8px; border: 1px solid #ddd;">' + year + '</td></tr>\n'
        '     <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>UNESCO Reference</strong></td><td style="padding: 8px; border: 1px solid #ddd;">[Reference]</td></tr>\n'
        '     <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Criteria</strong></td><td style="padding: 8px; border: 1px solid #ddd;">[Criteria]</td></tr>\n'
        '   </table>\n'
        '   Do NOT use <h1>, <h2>, or <h3> tags for table rows. Use only <table>, <tr>, and <td> elements.\n\n'
        '   <h2>\U0001f9f3 Visitor\'s Guide</h2>\n'
        '   <p style="margin: 2px 0; line-height: 1.35;">Access \u2014 [How to reach]</p>\n'
        '   <p style="margin: 2px 0; line-height: 1.35;">Best Time to Visit \u2014 [Season]</p>\n'
        '   <p style="margin: 2px 0; line-height: 1.35;">Permits \u2014 [If any]</p>\n'
        '   <p style="margin: 2px 0; line-height: 1.35;">Activities \u2014 [What to do]</p>'
        '   <p style="margin: 2px 0; line-height: 1.35;">What to Bring \u2014 [Essentials]</p>\n'
        '   <p style="margin: 2px 0; line-height: 1.35;">Etiquette \u2014 [Behavior rules]</p>\n\n'
        '   <h2>\U0001f4cd Location Map</h2>\n'
        '   <div style="margin: 30px 0;"><iframe height="400" loading="lazy" referrerpolicy="no-referrer-when-downgrade" src="https://www.google.com/maps?q=[LAT],[LON]&z=12&output=embed" style="border: 0; border-radius: 6px;" width="100%"></iframe></div>\n'
        '   <p style="font-size: 0.9em; color: #666; margin-top: 8px;">Map showing the location of ' + topic + '. Coordinates: [LAT], [LON]</p>\n\n'
        '   <h2>\U0001f4da Sources and Further Reading</h2>\n'
        '   <p>UNESCO World Heritage Centre \u2014 ' + topic + ': https://whc.unesco.org/en/list/[REF]</p>\n'
        '   <p>IUCN World Heritage Outlook \u2014 ' + topic + ': https://worldheritageoutlook.iucn.org/explore-sites/[slug]</p>\n'
        '   <p>Wikipedia \u2014 ' + topic + ': https://en.wikipedia.org/wiki/[slug]</p>\n'
        '   (add 2-3 more sources)\n\n'
        'IMPORTANT: Use the SAME latitude,longitude coordinates in the Summary Table "Coordinates" row, the Location Map iframe src, and the map caption. Replace [LAT],[LON] with actual decimal coordinates (e.g., 4.5333,36.3333).\n\n'
        '8. DO NOT include: <html>, <head>, <body>, , <figure>, <figcaption>, or any image tags.\n'
        '9. DO NOT include the sidebar support banner (engine adds it).\n'
        '10. RETURN ONLY RAW HTML \u2014 no markdown, no code fences, no explanations.\n\n'
        'JSON-LD SCHEMA (copy exactly, use the topic as headline):\n'
        '<script type="application/ld+json">{\n'
        '    "@context": "https://schema.org",\n'
        '    "@type": "BlogPosting",\n'
        '    "headline": "' + topic + '",\n'
        '    "author": {\n'
        '        "@type": "Person",\n'
        '        "name": "Nasir A Naqvi"\n'
        '    }\n'
        '}</script>'
    )
    return prompt


def test_api():
    print("Testing API connectivity...")
    for model_name in MODELS_TO_TEST:
        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": "Reply with exactly: MODEL_OK"}],
                    max_tokens=10
                )
                if "MODEL_OK" in response.choices[0].message.content:
                    print(f"API Test Successful. Using model: {model_name}")
                    return model_name
            except Exception as e:
                if "404" in str(e) or "model_not_found" in str(e).lower():
                    print(f"  [{model_name} not available] Trying next model...")
                    break
                print(f"  [{model_name} error] {e}")
                break
    print("All models failed during testing.")
    return None


REGISTRY_PATH = Path(r"D:\Projects\AutoPilot_OS_v2\content\post_registry.json")


def get_recent_posts(limit=20):
    """Read most recent posts from post_registry.json, deduplicated by post_id."""
    if not REGISTRY_PATH.exists():
        return []
    with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
        registry = json.load(f)
    seen = {}
    for key, entry in registry.items():
        post_id = entry.get('post_id', '')
        updated = entry.get('updated', '')
        if post_id and post_id not in seen:
            seen[post_id] = entry
        elif post_id and updated > seen[post_id].get('updated', ''):
            seen[post_id] = entry
    posts = sorted(seen.values(), key=lambda e: e.get('updated', ''), reverse=True)
    recent = posts[:limit]
    result = []
    for entry in recent:
        title = entry.get('title', '')
        slug = entry.get('slug', '')
        if title and slug:
            url = f"https://dustanddynasty.blogspot.com/2026/10/{slug}.html"
            result.append((title, url))
    return result


def call_llm(model_name: str, system_prompt: str, user_prompt: str) -> str:
    """Call the LLM and return raw response text."""
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=8000
    )
    return response.choices[0].message.content


def extract_html(full_response: str) -> str:
    """Extract HTML from LLM response, cleaning markdown fences."""
    html = full_response
    # Remove markdown code fences
    html = re.sub(r'^```html\s*', '', html, flags=re.IGNORECASE)
    html = re.sub(r'^```\s*', '', html)
    html = re.sub(r'\s*```$', '', html)
    
    # Find first HTML tag
    start_index = html.find("<")
    if start_index != -1:
        html = html[start_index:]
    
    # Ensure starts with <h1>
    if not re.search(r"<h1\b", html, flags=re.IGNORECASE):
        # This shouldn't happen if prompt is followed, but safety net
        pass
    
    return html


def main():
    model_name = test_api()
    if not model_name:
        print("Aborting. API connection failed entirely.")
        return

    # CLI argument handling
    cli_title = sys.argv[1] if len(sys.argv) > 1 else None

    print("[Generator] Loading next topic...")
    topic, country, year = load_next_topic(cli_title)
    
    if not topic:
        print("[ERROR] No topics remaining")
        return
    
    # FIX #3: Strip HTML tags from topic (CSV may contain <br />, <small>, etc.)
    if BEAUTIFULSOUP_AVAILABLE and BeautifulSoup:
        topic = BeautifulSoup(topic, "html.parser").get_text().strip()
    else:
        # Fallback: regex strip
        topic = re.sub(r'<[^>]+>', '', topic).strip()
    
    print(f"[Generator] Topic: {topic} ({country}, {year})")

    # Competitive Research Node
    competitor_angles = competitive_research(topic)

    recent_posts = get_recent_posts(limit=20)
    if recent_posts:
        print(f"[Generator] Injected {len(recent_posts)} recent posts for internal linking.")

    system_prompt = (
        "You are a professional UNESCO World Heritage travel writer. "
        "Output ONLY raw HTML. ONLY use URLs from the INTERNAL LINKING list provided above. "
        "Do not invent, guess, or include any other URLs. Ensure proper spacing between all words. "
        "Do not concatenate words. For the Summary Table of Facts, you MUST use a valid HTML "
        "<table> with <tr> and <td> elements. Do NOT use <h1>, <h2>, or <h3> tags for data rows."
    )

    # --- GENERATION LOOP (max 2 calls: initial + 1 revision) ---
    final_html = None
    first_draft_html = None  # Keep first draft as fallback
    final_score = 0
    final_errors = []
    
    for revision_num in range(MAX_REVISIONS + 1):  # 0 = initial, 1 = revision
        if revision_num == 0:
            print(f"[Generator] Calling LLM (initial generation) with model {model_name}...")
            user_prompt = build_prompt(topic, country, year, competitor_angles, internal_links=recent_posts)
        else:
            print(f"[Generator] Calling LLM (revision 1/{MAX_REVISIONS}) - Score was {final_score}/100")
            error_list = "\n".join(f"- {e}" for e in final_errors)
            user_prompt = (
                f"Your article scored {final_score}/100. Fix these specific errors:\n{error_list}\n\n"
                f"You MUST retain the JSON-LD schema, the <!--more--> tag, exactly 7 <h2> tags, "
                f"and the internal link. Return the fully rewritten HTML."
            )
        
        try:
            full_response = call_llm(model_name, system_prompt, user_prompt)
            html = extract_html(full_response)
            
            # Score the article
            result = score_article(html, topic)
            final_score = result['score']
            final_errors = result['errors']
            
            print(f"[Quality] Score: {final_score}/100")
            if final_errors:
                for err in final_errors:
                    print(f"  - {err}")
            
            if final_score >= QUALITY_THRESHOLD:
                print(f"[Quality] PASS (threshold {QUALITY_THRESHOLD})")
                final_html = html
                break
            elif revision_num < MAX_REVISIONS:
                # Save first draft as fallback
                if first_draft_html is None:
                    first_draft_html = html
                print(f"[Quality] FAIL - will attempt revision")
                continue
            else:
                print(f"[WARNING] Article failed quality check after {MAX_REVISIONS + 1} attempt(s).")
                # Goldfish fix: Use first draft if revision failed quality, else use revision
                if first_draft_html:
                    print(f"[Quality] Falling back to first draft (was cleaner).")
                    final_html = first_draft_html
                else:
                    final_html = html
                break
                
        except Exception as e:
            print(f"[ERROR] LLM call failed: {e}")
            if revision_num == 0:
                # If initial call fails completely, we have nothing
                print("[ERROR] Initial generation failed. Aborting.")
                return
            else:
                # If revision fails, use first draft
                print("[ERROR] Revision failed. Falling back to first draft.")
                final_html = first_draft_html
                break
    
    if not final_html:
        print("[ERROR] No HTML generated.")
        return

    # Save to pending
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    filename = slugify(topic) + ".html"
    output_path = PENDING_DIR / filename

    # Inject ORIGINAL_TOPIC comment for master-list removal matching
    html_with_topic = f"<!-- ORIGINAL_TOPIC: {topic} -->\n{final_html}"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_with_topic)

    print(f"[Generator] Saved draft to: {output_path}")
    print(f"[Generator] Final Quality Score: {final_score}/100")
    print(f"[Generator] Topic: {topic}")

    # Automatically trigger the main publisher engine
    publisher_script = Path(__file__).resolve().parent / "safe_batch.py"
    print(f"[Generator] Triggering publisher: {publisher_script}")
    venv_exe = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable
    result = subprocess.run(
        [venv_exe, str(publisher_script)],
        cwd=str(Path(__file__).resolve().parent),
    )
    if result.returncode != 0:
        print(f"[ERROR] safe_batch.py exited with code {result.returncode}")
        return


if __name__ == "__main__":
    main()