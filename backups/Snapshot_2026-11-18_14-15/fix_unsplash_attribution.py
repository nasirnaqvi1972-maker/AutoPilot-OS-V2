#!/usr/bin/env python3
"""
Fix Unsplash Attribution

Reads the audit snapshot JSON, finds <img> tags with unsplash.com in src,
and inserts attribution paragraph after each image.
"""

import argparse
import json
import sys
import shutil
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup


SNAPSHOT_PATH = Path(r"D:\Projects\AutoPilot_OS_v2\content\image_audit_20261020\audit_v2_posts_snapshot.json")
BACKUP_DIR = Path(r"D:\Projects\AutoPilot_OS_v2\backups")


def fix_unsplash_attribution(content: str) -> tuple[str, int]:
    """Fix unsplash attribution in HTML content. Returns (fixed_content, count_added)."""
    soup = BeautifulSoup(content, 'html.parser')
    added = 0
    
    for img in soup.find_all('img'):
        src = img.get('src', '')
        if 'unsplash.com' in src:
            # Check if attribution already exists (next sibling)
            next_sib = img.find_next_sibling()
            has_attribution = False
            if next_sib and next_sib.name == 'p':
                if 'Image source: Unsplash' in next_sib.get_text():
                    has_attribution = True
            
            if not has_attribution:
                # Create attribution paragraph
                attr_p = soup.new_tag('p')
                attr_p['style'] = 'font-size: 0.8em; color: gray; text-align: center;'
                i_tag = soup.new_tag('i')
                i_tag.string = 'Image source: Unsplash'
                attr_p.append(i_tag)
                
                # Insert after the image's parent (the <a> wrapper) or the img itself
                parent_a = img.find_parent('a')
                if parent_a:
                    parent_a.insert_after(attr_p)
                else:
                    img.insert_after(attr_p)
                added += 1
    
    return str(soup), added


def main():
    parser = argparse.ArgumentParser(description='Fix Unsplash attribution in blog posts')
    parser.add_argument('--in-place', action='store_true', help='Write changes to file (default: dry-run)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed (default)')
    args = parser.parse_args()
    
    # Default to dry-run if neither specified
    if not args.in_place and not args.dry_run:
        args.dry_run = True
    
    if not SNAPSHOT_PATH.exists():
        print(f"ERROR: Snapshot not found at {SNAPSHOT_PATH}")
        sys.exit(1)
    
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(SNAPSHOT_PATH, 'r', encoding='utf-8') as f:
        posts = json.load(f)
    
    total_posts = len(posts)
    affected_posts = 0
    total_attributions = 0
    
    print(f"Scanning {total_posts} posts...")
    
    for post in posts:
        content = post.get('content', '')
        fixed_content, added = fix_unsplash_attribution(content)
        
        if added > 0:
            affected_posts += 1
            total_attributions += added
            post['content'] = fixed_content
            print(f"  Post {post.get('id')}: {added} attribution(s) added")
    
    print(f"\nPosts affected: {affected_posts}")
    print(f"Total attributions added: {total_attributions}")
    
    if args.dry_run:
        print("\nDRY RUN - no changes written. Use --in-place to apply.")
        return
    
    # Create timestamped backup
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    backup_path = BACKUP_DIR / f"audit_v2_posts_snapshot.{timestamp}.bak"
    shutil.copy2(SNAPSHOT_PATH, backup_path)
    print(f"Backup written: {backup_path}")
    
    # Atomic write
    temp_path = SNAPSHOT_PATH.with_suffix('.tmp')
    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    temp_path.replace(SNAPSHOT_PATH)
    print(f"Saved changes in-place (atomic write): {SNAPSHOT_PATH}")


if __name__ == '__main__':
    main()
