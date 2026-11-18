import requests
import time
import re
from pathlib import Path

ROOT = Path(r"D:\Projects\AutoPilot_OS_v2")
URL_FILE = ROOT / "URL.txt"
OUTPUT_DIR = ROOT / "wayback_originals"

# Add a fake browser user-agent so the Wayback Machine doesn't instantly block us
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def clean_filename(url):
    match = re.search(r'/([^/]+\.html)', url)
    if match:
        filename = match.group(1)
        date_match = re.search(r'/(\d{4}/\d{2})/', url)
        if date_match:
            prefix = date_match.group(1).replace('/', '-')
            return f"{prefix}_{filename}"
        return filename
    return "unknown.html"

def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    if not URL_FILE.exists():
        print(f"Error: {URL_FILE} not found.")
        return

    print("Parsing URL list...")
    urls_to_download = {}
    
    with open(URL_FILE, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) < 3:
                continue
            
            raw_url = parts[0].strip()
            timestamp_date = parts[2].strip()
            
            if "archaeology-pak.blogspot.com" in raw_url and raw_url.endswith(".html"):
                if "/2011/" in raw_url or "/2012/" in raw_url:
                    normalized_url = re.sub(r'^https?://(www\.)?', 'https://', raw_url)
                    normalized_url = normalized_url.replace(':80', '')
                    
                    year_match = re.search(r'(\d{4})', timestamp_date)
                    year = year_match.group(1) if year_match else "2020"
                    
                    filename = clean_filename(normalized_url)
                    urls_to_download[filename] = (normalized_url, year)

    print(f"Found {len(urls_to_download)} unique original posts.\n")

    for filename, (url, year) in urls_to_download.items():
        output_path = OUTPUT_DIR / filename
        
        # Skip files we already downloaded successfully
        if output_path.exists():
            print(f"Skipping {filename} (already downloaded)")
            continue

        wayback_url = f"https://web.archive.org/web/{year}id_/{url}"
        print(f"Downloading: {filename}...")
        
        max_retries = 3
        success = False
        
        for attempt in range(max_retries):
            try:
                response = requests.get(wayback_url, headers=HEADERS, timeout=20)
                
                if response.status_code == 200:
                    with open(output_path, "w", encoding="utf-8") as out_f:
                        out_f.write(response.text)
                    print(f"  [OK] Saved.")
                    success = True
                    break # Success, exit retry loop
                    
                elif response.status_code == 429:
                    print(f"  [RATE LIMITED] Sleeping for 20 seconds... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(20)
                else:
                    print(f"  [FAILED] HTTP Status: {response.status_code}")
                    break
                    
            except Exception as e:
                print(f"  [ERROR] {e}")
                time.sleep(10)
        
        # Sleep between different files to avoid triggering the limit again
        time.sleep(10)

    print(f"\nDownload complete! Check the folder: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()