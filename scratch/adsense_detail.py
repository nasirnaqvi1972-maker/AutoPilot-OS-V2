import json
from pathlib import Path
from collections import Counter

data = json.loads(Path("scratch/adsense_data.json").read_text(encoding="utf-8"))

# 1. What ARE the "unsafe links"?
print("=== UNSAFE LINK SAMPLES ===")
for rec in data["unsafe_link_posts"][:5]:
    print(f"\n  Post: {rec['title'][:60]}")
    for lnk in rec["unsafe_links"][:5]:
        print(f"    {lnk}")

# 2. AI signal posts
print("\n=== AI SIGNAL POSTS ===")
for rec in data["ai_signal_posts"]:
    print(f"  [{rec['id']}] {rec['title'][:65]}")
    print(f"    Hits: {rec['ai_hits']}")

# 3. Duplicate title groups
print("\n=== DUPLICATE TITLE GROUPS ===")
for base, posts in data["duplicate_title_groups"].items():
    if len(posts) > 1:
        print(f"  Base: '{base[:60]}'")
        for pp in posts:
            print(f"    - [{pp['id']}] {pp['title'][:70]}")

# 4. Thin meta signal (intro < 30 words)
print("\n=== THIN INTRO (first <p> < 30 words) SAMPLE ===")
for rec in data["thin_meta_posts"][:10]:
    print(f"  [{rec['id']}] intro_words={rec['intro_words']} | {rec['title'][:60]}")

# 5. No Wikimedia attribution
print(f"\n=== NO WIKIMEDIA ATTRIBUTION: {data['summary']['no_wiki_attr_count']} posts ===")
for rec in data["no_wiki_attr_posts"][:8]:
    print(f"  [{rec['id']}] wiki_imgs={rec['wiki_imgs']} | {rec['title'][:60]}")

# 6. Word count distribution
all_r = data["all_results"]
bands = Counter()
for r in all_r:
    w = r["words"]
    if w < 500:   bands["<500"] += 1
    elif w < 1000: bands["500-999"] += 1
    elif w < 2000: bands["1000-1999"] += 1
    elif w < 3000: bands["2000-2999"] += 1
    else:          bands["3000+"] += 1
print("\n=== WORD COUNT DISTRIBUTION ===")
for k in ["<500","500-999","1000-1999","2000-2999","3000+"]:
    print(f"  {k}: {bands[k]}")

# 7. Monetisation link types
print("\n=== MONETISATION LINK TYPES ACROSS ALL POSTS ===")
mon_types = Counter()
for r in all_r:
    for lnk in r["mon_links"]:
        if "gumroad" in lnk:   mon_types["gumroad"] += 1
        if "patreon" in lnk:   mon_types["patreon"] += 1
        if "buymeacoffee" in lnk: mon_types["buymeacoffee"] += 1
        if "ko-fi" in lnk:     mon_types["ko-fi"] += 1
        if "paypal" in lnk:    mon_types["paypal"] += 1
print(dict(mon_types))
print(f"Total posts with any monetisation link: {data['summary']['mon_posts_count']}")
