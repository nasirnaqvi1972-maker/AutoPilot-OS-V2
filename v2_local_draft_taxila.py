import json
import time
from pathlib import Path
import trafilatura

UNESCO_URL = "https://whc.unesco.org/en/list/139/"
INVENTORY_FILE = Path("verified_inventory.json")
DRAFTS_DIR = Path("drafts")

def main():
    # 1. Create drafts folder
    DRAFTS_DIR.mkdir(exist_ok=True)
    
    # 2. Find Taxila in our verified inventory
    print("Searching verified inventory for Taxila...")
    with open(INVENTORY_FILE, "r", encoding="utf-8") as f:
        inventory = json.load(f)
        
    taxila_id = None
    for pid, data in inventory["posts"].items():
        if "taxila" in data["title"].lower():
            taxila_id = pid
            print(f"Found: {data['title']} (ID: {taxila_id})")
            break
            
    if not taxila_id:
        print("ERROR: Taxila not found in inventory.")
        return

    # 3. Scrape the UNESCO source (Agent 1's rule: rate limit)
    print(f"Scraping UNESCO source: {UNESCO_URL}")
    time.sleep(3) # Respectful delay
    
    downloaded = trafilatura.fetch_url(UNESCO_URL)
    if not downloaded:
        print("ERROR: Could not download UNESCO page.")
        return
        
    text = trafilatura.extract(downloaded)
    if not text:
        print("ERROR: Could not extract text from UNESCO page.")
        return

    # 4. Save the raw source text for your reference
    source_file = DRAFTS_DIR / "taxila_unesco_source.txt"
    with open(source_file, "w", encoding="utf-8") as f:
        f.write(text)
        
    print(f"\nSUCCESS: Source text saved to {source_file}")
    print("NEXT STEP: Open this file, copy the text, and use it with the DeepSeek prompt in ChatGPT/Claude.")
    print(f"Remember to save the AI output as: {DRAFTS_DIR / 'taxila_revision.html'}")

if __name__ == "__main__":
    main()