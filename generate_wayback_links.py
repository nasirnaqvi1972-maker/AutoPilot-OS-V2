import re
from pathlib import Path

ROOT = Path(r"D:\Projects\AutoPilot_OS_v2")
URL_FILE = ROOT / "URL.txt"
OUTPUT_HTML = ROOT / "wayback_links.html"

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
    if not URL_FILE.exists():
        print(f"Error: {URL_FILE} not found.")
        return

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

    # Generate HTML file with clickable links
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write("<html><head><title>Download Original Posts</title><style>")
        f.write("body { font-family: sans-serif; max-width: 800px; margin: 40px auto; line-height: 1.6; }")
        f.write("li { margin-bottom: 15px; }")
        f.write("a { color: #0066cc; font-weight: bold; }")
        f.write(".filename { color: #666; font-size: 0.9em; display: block; margin-top: 4px; }")
        f.write("</style></head><body>")
        f.write("<h1>Download Original Human Posts</h1>")
        f.write("<p>Click each link below. When the page loads, right-click and select <b>Save Page As...</b> and save it into your <code>wayback_originals</code> folder.</p><ol>")
        
        for filename, (url, year) in urls_to_download.items():
            # id_ tells wayback to serve raw HTML without their toolbar
            wayback_url = f"https://web.archive.org/web/{year}id_/{url}"
            
            f.write("<li>")
            f.write(f"<a href='{wayback_url}' target='_blank'>Open Original Post</a>")
            f.write(f"<span class='filename'>Save as: {filename}</span>")
            f.write("</li>")
            
        f.write("</ol></body></html>")

    print(f"Success! Generated link file: {OUTPUT_HTML}")
    print("Opening it in your browser now...")
    
    # Automatically open the HTML file in the default browser
    import webbrowser
    webbrowser.open(f"file:///{OUTPUT_HTML}")

if __name__ == "__main__":
    main()