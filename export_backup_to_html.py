import json
import re
from pathlib import Path

# The backup file we found
BACKUP_FILE = Path(r"D:\Projects\Auto Pilot OS\FULL_BACKUP_FIXED_20261020\perfect_live_blog_backup.json")

# The new folder to save the HTML files
OUTPUT_DIR = Path(r"D:\Projects\AutoPilot_OS_v2\old post backup")

def sanitize_filename(title):
    """Convert title to a safe Windows filename."""
    # Remove characters that are illegal in Windows filenames
    safe_title = re.sub(r'[<>:"/\\|?*]', '', title)
    # Replace spaces and dashes with underscores
    safe_title = safe_title.replace(' ', '_').replace('—', '-')
    # Trim to avoid file path length errors
    return safe_title[:100].strip('_')

def extract_posts(data, posts_dict):
    """Recursively find posts in the JSON tree."""
    if isinstance(data, dict):
        # Check if this dictionary is a post
        if 'title' in data and ('content' in data or 'html_content' in data):
            title = data.get('title', 'Untitled')
            content = data.get('content') or data.get('html_content')
            if content:
                # Use title as key to automatically deduplicate
                posts_dict[title] = content
                
        # Keep searching inside the dictionary
        for value in data.values():
            extract_posts(value, posts_dict)
            
    elif isinstance(data, list):
        # Keep searching inside the list
        for item in data:
            extract_posts(item, posts_dict)

def main():
    if not BACKUP_FILE.exists():
        print(f"Error: Could not find {BACKUP_FILE}")
        return

    # Create the output folder if it doesn't exist
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Created directory: {OUTPUT_DIR}")

    print("Reading backup JSON...")
    with open(BACKUP_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    posts = {}
    extract_posts(data, posts)
    
    print(f"Found {len(posts)} unique posts in the backup.")
    print("Exporting to HTML files...")

    count = 0
    for title, content in posts.items():
        filename = sanitize_filename(title) + ".html"
        filepath = OUTPUT_DIR / filename
        
        # Wrap the content in a basic HTML structure so it renders properly in a browser
        html_document = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }}
        img {{ max-width: 100%; height: auto; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <hr>
    {content}
</body>
</html>"""

        with open(filepath, 'w', encoding='utf-8') as out_file:
            out_file.write(html_document)
        
        count += 1
        if count % 20 == 0:
            print(f"  Exported {count}/{len(posts)}...")

    print(f"\nSUCCESS! Exported {count} posts to:")
    print(OUTPUT_DIR)
    print("You can now open this folder in Windows File Explorer and double-click any HTML file to read it in your browser.")

if __name__ == "__main__":
    main()