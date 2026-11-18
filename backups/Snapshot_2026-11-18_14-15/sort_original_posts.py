import os
import json
import re
from pathlib import Path
from datetime import datetime

DIRECTORIES = [
    Path(r"D:\Projects\AutoPilot_OS_v2"),
    Path(r"D:\Projects\Auto Pilot OS")
]

OUTPUT_FILE = Path(r"D:\Projects\AutoPilot_OS_v2\sorted_original_posts.txt")

AUTOPILOT_MARKERS = [
    "📍 Location:", "📅 Period:", "🏷️ Category:", 
    "Summary Table", "Visitor's Guide", "Human Connection"
]

def extract_date_from_json(node):
    if isinstance(node, dict):
        # Check for published date
        pub = node.get('published')
        if isinstance(pub, dict):
            return pub.get('$t')
        elif isinstance(pub, str):
            return pub
            
        for val in node.values():
            res = extract_date_from_json(val)
            if res: return res
    elif isinstance(node, list):
        for item in node:
            res = extract_date_from_json(item)
            if res: return res
    return None

def main():
    print("Scanning and extracting dates for original/human posts...")
    
    found_posts = []

    for base_dir in DIRECTORIES:
        if not base_dir.exists():
            continue
            
        for filepath in base_dir.rglob('*'):
            if filepath.is_file() and filepath.suffix.lower() in ['.json', '.html']:
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Skip AutoPilot files
                    if any(marker in content for marker in AUTOPILOT_MARKERS):
                        continue
                        
                    title = filepath.name
                    date_str = None
                    
                    if filepath.suffix.lower() == '.json':
                        try:
                            data = json.loads(content)
                            # Try to get title and date from JSON structure
                            def find_meta(n):
                                nonlocal title, date_str
                                if isinstance(n, dict):
                                    if 'title' in n and ('content' in n or 'html_content' in n):
                                        raw_title = n.get('title')
                                        if isinstance(raw_title, dict):
                                            title = str(raw_title.get('$t', title))
                                        else:
                                            title = str(raw_title)
                                        
                                        d = n.get('published')
                                        if isinstance(d, dict): date_str = d.get('$t')
                                        elif isinstance(d, str): date_str = d
                                        if date_str: return True
                                    for v in n.values():
                                        if find_meta(v): return True
                                elif isinstance(n, list):
                                    for i in n:
                                        if find_meta(i): return True
                                return False
                            find_meta(data)
                        except:
                            pass
                    
                    # Fallback date extraction via Regex for HTML or if JSON failed
                    if not date_str:
                        # Look for standard date patterns like 2011-08-09
                        match = re.search(r'(20[0-2][0-9]-[0-1][0-9]-[0-3][0-9])', content)
                        if match:
                            date_str = match.group(1)
                    
                    # Parse the date, fallback to file modification time if missing
                    if date_str:
                        try:
                            dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
                        except:
                            dt = datetime.fromtimestamp(filepath.stat().st_mtime)
                    else:
                        dt = datetime.fromtimestamp(filepath.stat().st_mtime)

                    found_posts.append({
                        "date": dt,
                        "title": title,
                        "filename": filepath.name
                    })
                    
                except Exception:
                    pass

    # Sort from oldest to newest
    found_posts.sort(key=lambda x: x["date"])

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"Total Original/Human Files Found: {len(found_posts)}\n")
        f.write("Format: [YYYY-MM-DD] | [Title] | [Filename]\n")
        f.write("=" * 80 + "\n\n")
        
        for post in found_posts:
            date_formatted = post["date"].strftime("%Y-%m-%d")
            f.write(f"[{date_formatted}] | {post['title']} | {post['filename']}\n")

    print(f"\nSorting complete! Open {OUTPUT_FILE} to view the list.")

if __name__ == "__main__":
    main()