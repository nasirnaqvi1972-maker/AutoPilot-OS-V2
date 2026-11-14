import csv
import time
import re
from pathlib import Path
import trafilatura

MISSING_FILE = Path("missing_sources.csv")
DRAFTS_DIR = Path("drafts")

# Dictionary of the missing UNESCO URLs
URL_MAP = {
    "budapest": "https://whc.unesco.org/en/list/400/",
    "alhambra": "https://whc.unesco.org/en/list/314/",
    "agra fort": "https://whc.unesco.org/en/list/251/",
    "tassili": "https://whc.unesco.org/en/list/179/",
    "kilwa": "https://whc.unesco.org/en/list/144/",
    "brasília": "https://whc.unesco.org/en/list/445/",
    "brasilia": "https://whc.unesco.org/en/list/445/",
    "angra do heroísmo": "https://whc.unesco.org/en/list/206/",
    "angra do heroismo": "https://whc.unesco.org/en/list/206/",
    "citadelle and sans-souci": "https://whc.unesco.org/en/list/180/",
    "portobelo and san lorenzo": "https://whc.unesco.org/en/list/135/",
    "stonehenge": "https://whc.unesco.org/en/list/373/",
    "old havana": "https://whc.unesco.org/en/list/204/",
    "al qal'a of beni hammad": "https://whc.unesco.org/en/list/102/",
    "ancient thebes": "https://whc.unesco.org/en/list/87/",
    "auschwitz": "https://whc.unesco.org/en/list/31/",
    "berat and gjirokaster": "https://whc.unesco.org/en/list/569/",
    "borobudur": "https://whc.unesco.org/en/list/592/",
    "butrint": "https://whc.unesco.org/en/list/570/",
    "carthage": "https://whc.unesco.org/en/list/37/",
    "costiera amalfitana": "https://whc.unesco.org/en/list/830/",
    "djémila": "https://whc.unesco.org/en/list/191/",
    "djemila": "https://whc.unesco.org/en/list/191/",
    "fasil ghebbi": "https://whc.unesco.org/en/list/19/",
    "great zimbabwe": "https://whc.unesco.org/en/list/364/",
    "ha long bay": "https://whc.unesco.org/en/list/672/",
    "hiroshima": "https://whc.unesco.org/en/list/775/",
    "lake ohrid": "https://whc.unesco.org/en/list/99/",
    "lord howe": "https://whc.unesco.org/en/list/186/",
    "machu picchu": "https://whc.unesco.org/en/list/274/",
    "memphis": "https://whc.unesco.org/en/list/86/",
    "mont-saint-michel": "https://whc.unesco.org/en/list/80/",
    "polonnaruwa": "https://whc.unesco.org/en/list/201/",
    "quirigua": "https://whc.unesco.org/en/list/149/",
    "robben island": "https://whc.unesco.org/en/list/916/",
    "lalibela": "https://whc.unesco.org/en/list/18/",
    "santa maria delle grazie": "https://whc.unesco.org/en/list/93/",
    "taj mahal": "https://whc.unesco.org/en/list/252/",
    "te wahipounamu": "https://whc.unesco.org/en/list/551/",
    "bamiyan": "https://whc.unesco.org/en/list/208/",
    "babylon": "https://whc.unesco.org/en/list/278/",
    "yellowstone": "https://whc.unesco.org/en/list/28/",
    "forbidden city": "https://whc.unesco.org/en/list/439/",
    "lumbini": "https://whc.unesco.org/en/list/666/",
    "great barrier reef": "https://whc.unesco.org/en/list/154/",
    "meidan emam": "https://whc.unesco.org/en/list/115/",
    "m'zab valley": "https://whc.unesco.org/en/list/188/",
    "minaret of jam": "https://whc.unesco.org/en/list/211/",
    "petra": "https://whc.unesco.org/en/list/326/",
    "primeval beech forests": "https://whc.unesco.org/en/list/1133/"
}

def main():
    if not MISSING_FILE.exists():
        print(f"No {MISSING_FILE} found.")
        return

    DRAFTS_DIR.mkdir(exist_ok=True)
    
    with open(MISSING_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Found {len(rows)} missing posts. Running automated patch...\n")

    success_count = 0
    skipped_local_count = 0

    for row in rows:
        title = row['title']
        title_lower = title.lower()
        
        # Try to find a matching URL in our dictionary (whole-word match to avoid false positives)
        import re as _re
        matched_url = None
        title_words = set(title_lower.replace('—', ' ').replace('|', ' ').replace('-', ' ').split())
        for key, url in URL_MAP.items():
            key_words = set(key.split())
            if key_words and key_words.issubset(title_words):
                matched_url = url
                break
            # Fallback: exact substring match for single-word keys
            if ' ' not in key and key in title_lower:
                matched_url = url
                break
        
        if not matched_url:
            print(f"[SKIP - LOCAL SITE] {title}")
            skipped_local_count += 1
            continue

        print(f"[FETCH] {title} -> {matched_url}")
        time.sleep(2) # Rate limit
        
        try:
            downloaded = trafilatura.fetch_url(matched_url)
            if downloaded:
                text = trafilatura.extract(downloaded)
                if text and len(text) > 500:
                    safe_filename = re.sub(r'[^a-zA-Z0-9]', '_', title)[:30].lower()
                    source_file = DRAFTS_DIR / f"{safe_filename}_source.txt"
                    
                    with open(source_file, "w", encoding="utf-8") as f:
                        f.write(text)
                    print(f"  [OK] Saved to {source_file.name}")
                    success_count += 1
                else:
                    print("  [WARN] Text extracted was too short.")
            else:
                print("  [ERROR] Could not download page.")
        except Exception as e:
            print(f"  [ERROR] {e}")

    print(f"\nFinished automated patching.")
    print(f"Added Sources: {success_count}")
    print(f"Skipped Local Sites: {skipped_local_count}")

if __name__ == "__main__":
    main()