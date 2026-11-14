"""
adsense_audit_data.py — Collects raw data for the AdSense audit report.
Run with the venv Python. Outputs JSON to scratch/adsense_data.json.
"""
import json, re, sys
from collections import Counter, defaultdict
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent.parent  # AutoPilot_OS_v2
SNAP = ROOT / "content" / "image_audit_20261020" / "audit_v2_posts_snapshot.json"

posts = json.loads(SNAP.read_text(encoding="utf-8"))
print(f"Loaded {len(posts)} posts", file=sys.stderr)

MON_DOMAINS   = ["buymeacoffee", "patreon", "gumroad", "ko-fi", "paypal"]
UNSAFE_PATTERNS = ["bit.ly", "tinyurl", "t.co", "ow.ly", "goo.gl", "adf.ly", "adfoc"]
INTERNAL_HOSTS  = {
    "dustanddynasty.blogspot.com",
    "blogger.com", "www.blogger.com",
    "bp.blogspot.com",
    "blogger.googleusercontent.com",
    "googleusercontent.com",
    "www.youtube.com", "youtube.com",
    "wikipedia.org", "en.wikipedia.org",
    "commons.wikimedia.org",
    "upload.wikimedia.org",
    "wikimedia.org",
}

AI_PHRASES = [
    "as an ai", "as a language model", "i cannot provide",
    "delve into", "it is worth noting", "in conclusion, it is clear",
    "the tapestry of", "a testament to", "stands as a testament",
    "in the annals of", "nestled in the heart of",
    "rich tapestry", "journey through time",
]

results = []

word_counts = []
titles = []
mon_posts = []
unsafe_link_posts = []
ext_link_counts = []
privacy_posts = []          # posts containing a privacy-policy link
wikimedia_no_attr = []
ai_signal_posts = []
title_duplicate_groups = defaultdict(list)
short_desc_posts = []       # posts where first paragraph < 50 words (thin intro)
double_title_posts = []     # title appears word-for-word in first <h1>/<h2>
empty_meta = []             # always all — Blogger posts don't embed meta in content

for p in posts:
    pid    = str(p.get("id",""))
    title  = p.get("title","")
    url    = p.get("url","")
    content = p.get("content","")
    soup   = BeautifulSoup(content, "html.parser")
    text   = soup.get_text(" ", strip=True)
    words  = len(text.split())
    word_counts.append(words)
    titles.append(title)

    # --- 1. Content quality ---
    # Word count
    thin = words < 500

    # AI phrases
    text_lower = text.lower()
    ai_hits = [ph for ph in AI_PHRASES if ph in text_lower]

    # Title similarity key (normalise)
    norm_title = re.sub(r"[^a-z0-9 ]", "", title.lower()).strip()
    # Strip " — subtitle" pattern for grouping
    base_title = norm_title.split("—")[0].strip().split("|")[0].strip()
    title_duplicate_groups[base_title].append({"id": pid, "title": title, "url": url})

    # First paragraph word count
    first_p = soup.find("p")
    intro_words = len(first_p.get_text().split()) if first_p else 0

    # --- 2. Monetisation ---
    all_hrefs = re.findall(r'href=["\']([^"\']+)', content)
    mon_links  = [h for h in all_hrefs if any(d in h for d in MON_DOMAINS)]
    mon_count  = len(set(mon_links))

    # Count how many times "support" / "buy me" / "coffee" appears in text
    support_hits = sum(1 for w in ["buy me a coffee","support this blog","support me on","become a patron","gumroad"] if w in text_lower)

    # --- 3. Policy / Copyright ---
    has_privacy  = any("privacy" in h.lower() and "policy" in text_lower for h in all_hrefs) or "privacy policy" in text_lower
    unsafe_links = [h for h in all_hrefs if any(u in h for u in UNSAFE_PATTERNS)]

    # Wikimedia images without attribution check
    imgs = soup.find_all("img")
    wiki_imgs = [i for i in imgs if "wikimedia" in (i.get("src","") + i.get("data-src","")).lower()
                 or "upload.wikimedia" in (i.get("src","") + i.get("data-src","")).lower()]
    # Look for attribution text near images
    has_attr = "wikimedia" in text_lower or "commons.wikimedia" in text_lower or "creative commons" in text_lower

    # --- 4. UX / Nav ---
    ext_links = [h for h in all_hrefs if h.startswith("http") and
                 not any(d in h for d in INTERNAL_HOSTS)]
    ext_count = len(ext_links)

    has_contact = any("contact" in h.lower() for h in all_hrefs)
    has_about   = any("about" in h.lower() for h in all_hrefs)

    # --- 5. Technical ---
    # Meta descriptions live in the theme, not post content.
    # We can flag posts with very short first-paragraph intros (< 30 words) as
    # candidates where auto-generated meta will be thin.
    thin_meta_signal = intro_words < 30

    # Collect record
    rec = {
        "id": pid, "title": title, "url": url,
        "words": words, "thin": thin,
        "ai_hits": ai_hits,
        "mon_links": list(set(mon_links)), "mon_count": mon_count,
        "support_hits": support_hits,
        "has_privacy": has_privacy,
        "unsafe_links": unsafe_links,
        "wiki_imgs": len(wiki_imgs), "has_wiki_attr": has_attr,
        "ext_count": ext_count,
        "intro_words": intro_words, "thin_meta_signal": thin_meta_signal,
    }
    results.append(rec)

    if ai_hits:
        ai_signal_posts.append(rec)
    if unsafe_links:
        unsafe_link_posts.append(rec)

# --- Duplicate title groups (base title appears for 2+ different posts) ---
dup_groups = {k: v for k, v in title_duplicate_groups.items() if len(v) > 1}

# --- Aggregate stats ---
total = len(results)
thin_posts = [r for r in results if r["thin"]]
mon_posts  = [r for r in results if r["mon_count"] > 0]
high_ext   = [r for r in results if r["ext_count"] > 10]
no_wiki_attr = [r for r in results if r["wiki_imgs"] > 0 and not r["has_wiki_attr"]]
thin_meta  = [r for r in results if r["thin_meta_signal"]]
all_have_privacy = sum(1 for r in results if r["has_privacy"])

summary = {
    "total_posts": total,
    "word_count_avg": round(sum(word_counts)/total),
    "word_count_min": min(word_counts),
    "word_count_max": max(word_counts),
    "thin_posts_count": len(thin_posts),
    "mon_posts_count": len(mon_posts),
    "ai_signal_count": len(ai_signal_posts),
    "unsafe_link_count": len(unsafe_link_posts),
    "no_wiki_attr_count": len(no_wiki_attr),
    "high_ext_link_count": len(high_ext),
    "thin_meta_signal_count": len(thin_meta),
    "posts_with_privacy_ref": all_have_privacy,
    "duplicate_title_groups": len(dup_groups),
}

out = {
    "summary": summary,
    "thin_posts": thin_posts[:20],
    "mon_posts_sample": mon_posts[:5],
    "mon_posts_all_ids": [r["id"] for r in mon_posts],
    "ai_signal_posts": ai_signal_posts[:20],
    "unsafe_link_posts": unsafe_link_posts[:20],
    "no_wiki_attr_posts": no_wiki_attr[:20],
    "high_ext_link_posts": high_ext[:20],
    "thin_meta_posts": thin_meta[:20],
    "duplicate_title_groups": dict(list(dup_groups.items())[:30]),
    "all_results": results,
}

OUT_PATH = Path(__file__).parent / "adsense_data.json"
import os, tempfile
fd, tmp = tempfile.mkstemp(dir=OUT_PATH.parent, suffix=".tmp")
with os.fdopen(fd, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
os.replace(tmp, OUT_PATH)
print(f"Written: {OUT_PATH}", file=sys.stderr)

# Print summary to stdout for quick read
print(json.dumps(summary, indent=2))
