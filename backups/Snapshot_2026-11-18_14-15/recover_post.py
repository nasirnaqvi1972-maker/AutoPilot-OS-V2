import json
import os
from pathlib import Path

# The backup folder we found
BACKUP_DIR = Path(r"D:\Projects\Auto Pilot OS\FULL_BACKUP_FIXED_20261020")
OUTPUT_FILE = Path(r"D:\Projects\AutoPilot_OS_v2\dulmial_recovered.html")

def find_post(data):
    """Recursively search JSON for the Dulmial post."""
    if isinstance(data, dict):
        # Check if this dictionary is the post we want
        title = str(data.get('title', ''))
        if "Dulmial" in title or "Victoria Gun" in title:
            # Extract content (handle different key names used in your backups)
            content = data.get('content') or data.get('html_content') or data.get('content_html')
            if content and len(str(content)) > 500: # Ensure it's not the truncated 140-word version
                return content
                
        # Search all values in the dictionary
        for value in data.values():
            result = find_post(value)
            if result: return result
            
    elif isinstance(data, list):
        # Search all items in the list
        for item in data:
            result = find_post(item)
            if result: return result
            
    return None

def main():
    print("Searching backups for the full Dulmial post...")
    
    if not BACKUP_DIR.exists():
        print(f"Error: Folder not found: {BACKUP_DIR}")
        return

    # Search all JSON files in the backup directory
    for filepath in BACKUP_DIR.glob("*.json"):
        print(f"Checking {filepath.name}...")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            content = find_post(data)
            if content:
                print(f"\nSUCCESS! Found the full post in {filepath.name}")
                with open(OUTPUT_FILE, 'w', encoding='utf-8') as out:
                    out.write(content)
                print(f"Saved the full HTML to: {OUTPUT_FILE}")
                print("You can now open this HTML file, copy the text, and paste it into Blogger.")
                return
        except Exception as e:
            print(f"  Skipped (not valid JSON or read error): {e}")
            
    print("\nCould not find the full post in this folder. Try checking the 'content/image_audit_FINAL' folder manually.")

if __name__ == "__main__":
    main()