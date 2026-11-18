import json
import time
import csv
import re
from pathlib import Path
import trafilatura

# NEW: Using the master CSV database
SITES_FILE = Path("sitesCSV.csv")
INVENTORY_FILE = Path("verified_inventory.json")
DRAFTS_DIR = Path("drafts")
MISSING_FILE = Path("missing_sources.csv")
BATCH_SIZE = 10

def load_site_registry():
    """Loads the massive sitesCSV.csv into a lookup dictionary."""
    registry = {}
    if not SITES_FILE.exists():
        print(f"ERROR: {SITES_FILE} not found.")
        return registry
        
    print("Parsing master UNESCO database (this may take a few seconds)...")
    with open(SITES_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            site_name = row.get('site_name', '').strip()
            id_no = row.get('id_no', '').strip()
            status = row.get('unesco_status', 'Listed').strip().lower()
            
            if site_name and id_no:
                # Store by lowercase name for easier matching
                registry[site_name.lower()] = {
                    "id": id_no,
                    "status": status
                }
    return registry

def get_unesco_url(site_title, registry):
    """Matches the Blogger title against the master database."""
    # Clean the title: "Agra Fort — The Sandstone Crown" -> "Agra Fort"
    clean_title = site_title.split('|')[0].split('—')[0].split('-')[0].strip().lower()
    
    # 1. Exact match
    if clean_title in registry:
        data = registry[clean_title]
        if data['status'] == 'tentative':
            return f"https://whc.unesco.org/en/tentativelists/{data['id']}/"
        return f"https://whc.unesco.org/en/list/{data['id']}/"
            
    # 2. Substring match (e.g., "agra fort" in "agra fort, india")
    for db_name, data in registry.items():
        if clean_title == db_name or clean_title in db_name or db_name in clean_title:
            if data['status'] == 'tentative':
                return f"https://whc.unesco.org/en/tentativelists/{data['id']}/"
            return f"https://whc.unesco.org/en/list/{data['id']}/"
                
    return None

def log_missing_record(post_id, title, reason):
    file_exists = MISSING_FILE.exists()
    with open(MISSING_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "title", "reason"])
        if not file_exists:
            writer.writeheader()
        writer.writerow({"id": post_id, "title": title, "reason": reason})

def main():
    DRAFTS_DIR.mkdir(exist_ok=True)

    registry = load_site_registry()
    if not registry:
        return
        
    print("Loading verified inventory...")
    with open(INVENTORY_FILE, "r", encoding="utf-8") as f:
        inventory = json.load(f)["posts"]

    posts_to_process = list(inventory.items())
    total_posts = len(posts_to_process)
    
    processed_count = 0
    skipped_existing = 0
    missing_count = 0
    batch_count = 0

    print(f"Starting extraction of {total_posts} posts using master database...")

    for post_id, data in posts_to_process:
        title = data['title']
        safe_filename = re.sub(r'[^a-zA-Z0-9]', '_', title)[:30].lower()
        source_file = DRAFTS_DIR / f"{safe_filename}_source.txt"

        if source_file.exists():
            skipped_existing += 1
            continue

        url = get_unesco_url(title, registry)
        
        if not url:
            log_missing_record(post_id, title, "Not found in sitesCSV.csv")
            print(f"[SKIP] {title} - Source missing.")
            missing_count += 1
            batch_count += 1
        else:
            print(f"[FETCH] {title} -> {url}")
            time.sleep(2) # Rate limit
            
            try:
                downloaded = trafilatura.fetch_url(url)
                if not downloaded:
                    log_missing_record(post_id, title, "Failed to download")
                    missing_count += 1
                else:
                    text = trafilatura.extract(downloaded)
                    if not text or len(text) < 500:
                        log_missing_record(post_id, title, "Extraction too short/empty")
                        print(f"  [WARN] Text too short. Flagged for review.")
                        missing_count += 1
                    else:
                        with open(source_file, "w", encoding="utf-8") as f:
                            f.write(text)
                        print(f"  [OK] Saved to {source_file.name}")
                        processed_count += 1
            except Exception as e:
                log_missing_record(post_id, title, str(e))
                missing_count += 1
                print(f"  [ERROR] {e}")
            
            batch_count += 1

        if batch_count >= BATCH_SIZE:
            print(f"\n--- BATCH OF {BATCH_SIZE} COMPLETE ---")
            print(f"Stats -> Extracted: {processed_count} | Missing: {missing_count} | Skipped: {skipped_existing}")
            print("Continuing automatically in 5 seconds...\n")
            time.sleep(5) 
            batch_count = 0

    print(f"\nFinished all {total_posts} posts.")
    print(f"Total Successful Extractions: {processed_count}")
    print(f"Total Skipped (Already Downloaded): {skipped_existing}")
    print(f"Total Missing/Failed (Saved to {MISSING_FILE}): {missing_count}")

if __name__ == "__main__":
    main()