import csv
import time
import re
from pathlib import Path
import trafilatura

MISSING_FILE = Path("missing_sources.csv")
DRAFTS_DIR = Path("drafts")

def main():
    if not MISSING_FILE.exists():
        print(f"No {MISSING_FILE} found.")
        return

    DRAFTS_DIR.mkdir(exist_ok=True)
    
    with open(MISSING_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Found {len(rows)} missing posts to patch.")
    print("For each post, paste the exact UNESCO URL and press Enter.")
    print("If it is NOT a UNESCO site (e.g., a local fort), just press Enter to skip.\n")

    success_count = 0

    for row in rows:
        title = row['title']
        print(f"\nPOST: {title}")
        
        url = input("Paste UNESCO URL (or press Enter to skip): ").strip()
        
        if not url:
            print("  -> Skipped (No URL provided).")
            continue
            
        if not url.startswith("http"):
            print("  -> Invalid URL. Skipped.")
            continue

        print(f"  [FETCH] Scraping {url}...")
        time.sleep(2) # Rate limit
        
        try:
            downloaded = trafilatura.fetch_url(url)
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
                    print("  [WARN] Text extracted was too short. Page might be blank.")
            else:
                print("  [ERROR] Could not download page.")
        except Exception as e:
            print(f"  [ERROR] {e}")

    print(f"\nFinished patching. Successfully added {success_count} new sources.")

if __name__ == "__main__":
    main()