import json
from pathlib import Path
from core.blogger_publisher import get_blogger_service

BLOG_URL = "https://dustanddynasty.blogspot.com"
POST_ID = "5156852846229382939" # Taxila's verified ID
HTML_FILE = Path("drafts/taxila_revision.html")
BACKUP_FILE = Path("backups/taxila_backup.json")

def main():
    if not HTML_FILE.exists():
        print(f"ERROR: Could not find {HTML_FILE}. Please create the draft first.")
        return

    print("Reading new HTML draft...")
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        new_html = f.read()

    print("Connecting to Blogger API...")
    service = get_blogger_service()
    blog = service.blogs().getByUrl(url=BLOG_URL).execute()
    blog_id = blog['id']

    # 1. Fetch current post for backup
    print("Fetching current live post for backup...")
    current_post = service.posts().get(blogId=blog_id, postId=POST_ID).execute()
    
    # Create backups directory and save
    BACKUP_FILE.parent.mkdir(exist_ok=True)
    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(current_post, f, indent=2)
    print(f"SUCCESS: Backup saved to {BACKUP_FILE}")

    # 2. Patch the post (Do NOT change status, it stays LIVE)
    print("Patching live post with new content...")
    body = {
        "content": new_html
    }

    try:
        result = service.posts().patch(blogId=blog_id, postId=POST_ID, body=body).execute()
        
        # 3. Verify the URL hasn't changed
        original_url = current_post.get('url')
        new_url = result.get('url')
        
        print("\n--- VERIFICATION ---")
        print(f"Original URL: {original_url}")
        print(f"New URL:      {new_url}")
        
        if original_url == new_url:
            print("\n[OK] URL preserved. The live post has been safely updated.")
        else:
            print("\n[WARNING] The URL changed! Investigate immediately.")
            
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    main()