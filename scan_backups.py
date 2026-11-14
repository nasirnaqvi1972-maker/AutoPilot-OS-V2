import os
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

DIRECTORIES = [
    Path(r"D:\Projects\AutoPilot_OS_v2"),
    Path(r"D:\Projects\Auto Pilot OS")
]

OUTPUT_FILE = Path(r"D:\Projects\AutoPilot_OS_v2\backup_inventory.txt")

AUTOPILOT_MARKERS = [
    "📍 Location:", "📅 Period:", "🏷️ Category:", 
    "Summary Table", "Visitor's Guide", "Human Connection"
]

def scan_file(filepath):
    posts_found = []
    
    if filepath.suffix.lower() == '.json':
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            def extract_posts(node):
                if isinstance(node, dict):
                    if 'title' in node and ('content' in node or 'html_content' in node):
                        content = node.get('content') or node.get('html_content') or ""
                        
                        # FIX: Force title and content to be strings
                        raw_title = node.get('title', 'Untitled')
                        if isinstance(raw_title, dict):
                            title = str(raw_title.get('$t', 'Untitled'))
                        else:
                            title = str(raw_title)
                            
                        content_str = str(content)
                        
                        is_autopilot = any(marker in content_str for marker in AUTOPILOT_MARKERS)
                        posts_found.append({
                            "title": title,
                            "is_autopilot": is_autopilot,
                            "length": len(content_str)
                        })
                    for val in node.values():
                        extract_posts(val)
                elif isinstance(node, list):
                    for item in node:
                        extract_posts(item)
            
            extract_posts(data)
            
        except Exception:
            pass 

    elif filepath.suffix.lower() == '.html':
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                html = f.read()
            
            soup = BeautifulSoup(html, 'html.parser')
            title_tag = soup.find('title')
            title_text = str(title_tag.get_text()) if title_tag else filepath.name
            
            is_autopilot = any(marker in html for marker in AUTOPILOT_MARKERS)
            posts_found.append({
                "title": title_text,
                "is_autopilot": is_autopilot,
                "length": len(html)
            })
        except Exception:
            pass
            
    return posts_found

def main():
    print("Scanning backups for original/human posts...")
    
    human_posts = []
    autopilot_posts = []
    file_count = 0

    for base_dir in DIRECTORIES:
        if not base_dir.exists():
            continue
            
        print(f"Scanning: {base_dir}...")
        
        for filepath in base_dir.rglob('*'):
            if filepath.is_file() and filepath.suffix.lower() in ['.json', '.html']:
                file_count += 1
                posts = scan_file(filepath)
                
                for post in posts:
                    if post['is_autopilot']:
                        autopilot_posts.append(post)
                    else:
                        human_posts.append(post)

    # Write Report
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"=== BACKUP SCAN REPORT ===\n")
        f.write(f"Scanned {file_count} files.\n\n")
        
        f.write(f"--- POTENTIAL HUMAN / ORIGINAL POSTS ({len(human_posts)}) ---\n")
        f.write("These do NOT have the AutoPilot template. They might be your 2011-2020 originals.\n")
        # FIX: Added str() to x['title'] to prevent sorting crash
        for p in sorted(human_posts, key=lambda x: str(x['title']).lower()):
            f.write(f"- {p['title']} (Length: {p['length']} chars)\n")
            
        f.write(f"\n--- AUTOPILOT TEMPLATE POSTS ({len(autopilot_posts)}) ---\n")
        for p in sorted(autopilot_posts, key=lambda x: str(x['title']).lower())[:30]:
            f.write(f"- {p['title']} (Length: {p['length']} chars)\n")
        if len(autopilot_posts) > 30:
            f.write(f"... and {len(autopilot_posts) - 30} more.\n")

    print(f"\nScan complete! Open {OUTPUT_FILE} to see the results.")

if __name__ == "__main__":
    main()