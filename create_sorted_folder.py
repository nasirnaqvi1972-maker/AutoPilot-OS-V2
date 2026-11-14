import os
import json
import re
import shutil
from pathlib import Path
from datetime import datetime

DIRECTORIES = [
    Path(r"D:\Projects\AutoPilot_OS_v2"),
    Path(r"D:\Projects\Auto Pilot OS")
]

# The new folder where everything will be copied
OUTPUT_DIR = Path(r"D:\Projects\AutoPilot_OS_v2\sorted_original_posts")

AUTOPILOT_MARKERS = [
    "📍 Location:", "📅 Period:", "🏷️ Category:", 
    "Summary Table", "Visitor's Guide", "Human Connection"
]

def main():
    print("Scanning and extracting original files...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    found_posts = []

    for base_dir in DIRECTORIES:
        if not base_dir.exists():
            continue
            
        for filepath in base_dir.rglob('*'):
            # Skip files already inside the output folder
            if OUTPUT_DIR in filepath.parents:
                continue
                
            if filepath.is_file() and filepath.suffix.lower() in ['.json', '.html']:
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Skip AutoPilot files
                    if any(marker in content for marker in AUTOPILOT_MARKERS):
                        continue
                        
                    date_str = None
                    
                    if filepath.suffix.lower() == '.json':
                        try:
                            data = json.loads(content)
                            def find_date(n):
                                if isinstance(n, dict):
                                    d = n.get('published')
                                    if isinstance(d, dict) and d.get('$t'): return d.get('$t')
                                    elif isinstance(d, str): return d
                                    for v in n.values():
                                        res = find_date(v)
                                        if res: return res
                                elif isinstance(n, list):
                                    for i in n:
                                        res = find_date(i)
                                        if res: return res
                                return None
                            date_str = find_date(data)
                        except:
                            pass
                    
                    if not date_str:
                        match = re.search(r'(20[0-2][0-9]-[0-1][0-9]-[0-3][0-9])', content)
                        if match:
                            date_str = match.group(1)
                    
                    if date_str:
                        try:
                            dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
                        except:
                            dt = datetime.fromtimestamp(filepath.stat().st_mtime)
                    else:
                        dt = datetime.fromtimestamp(filepath.stat().st_mtime)

                    found_posts.append({
                        "date": dt,
                        "date_str": dt.strftime("%Y-%m-%d"),
                        "original_name": filepath.name,
                        "filepath": filepath
                    })
                    
                except Exception:
                    pass

    # Sort from oldest to newest
    found_posts.sort(key=lambda x: x["date"])

    print(f"Copying {len(found_posts)} files to {OUTPUT_DIR}...")

    # Copy files with a date prefix so Windows Explorer sorts them automatically
    for index, post in enumerate(found_posts, start=1):
        new_filename = f"{index:03d}_{post['date_str']}_{post['original_name']}"
        dest_path = OUTPUT_DIR / new_filename
        
        try:
            shutil.copy2(post['filepath'], dest_path)
        except Exception as e:
            print(f"Failed to copy {post['original_name']}: {e}")

    print("\nDONE! All files are copied and sorted.")

if __name__ == "__main__":
    main()