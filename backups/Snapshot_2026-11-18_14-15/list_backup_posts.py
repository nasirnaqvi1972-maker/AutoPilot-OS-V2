import json
from pathlib import Path

# The backup file we found earlier
BACKUP_FILE = Path(r"D:\Projects\Auto Pilot OS\FULL_BACKUP_FIXED_20261020\perfect_live_blog_backup.json")
OUTPUT_FILE = Path(r"D:\Projects\AutoPilot_OS_v2\backup_post_list.txt")

def extract_posts(data, posts_list):
    """Recursively search the JSON for dictionaries containing a title and URL."""
    if isinstance(data, dict):
        # Check if this dictionary looks like a post
        if 'title' in data and ('url' in data or 'id' in data):
            title = data.get('title', 'Untitled')
            url = data.get('url', 'No URL')
            posts_list.append(f"{title} | {url}")
            
        # Keep searching inside the dictionary
        for value in data.values():
            extract_posts(value, posts_list)
            
    elif isinstance(data, list):
        # Keep searching inside the list
        for item in data:
            extract_posts(item, posts_list)

def main():
    if not BACKUP_FILE.exists():
        print(f"Error: Could not find {BACKUP_FILE}")
        return

    print(f"Reading {BACKUP_FILE.name}...")
    with open(BACKUP_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    posts = []
    extract_posts(data, posts)
    
    # Remove duplicates (if the JSON has nested duplicates)
    unique_posts = list(set(posts))
    unique_posts.sort()

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"Total Unique Posts in Backup: {len(unique_posts)}\n")
        f.write("=" * 60 + "\n\n")
        for post in unique_posts:
            f.write(post + "\n")

    print(f"Success! Extracted {len(unique_posts)} posts.")
    print(f"Open this file to see the list: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()