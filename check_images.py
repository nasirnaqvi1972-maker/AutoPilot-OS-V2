#!/usr/bin/env python3
"""
check_images.py - Count images in audit snapshot and generate markdown report
"""

import json
from pathlib import Path
from bs4 import BeautifulSoup

SNAPSHOT_PATH = Path(r"D:\Projects\AutoPilot_OS_v2\content\image_audit_20261020\audit_v2_posts_snapshot.json")
REPORT_PATH = Path(r"D:\Projects\AutoPilot_OS_v2\IMAGE_REPORT.md")

def main():
    with open(SNAPSHOT_PATH, 'r', encoding='utf-8') as f:
        posts = json.load(f)

    total_posts = len(posts)
    total_images = 0
    posts_under_7 = []

    for post in posts:
        content = post.get('content', '')
        soup = BeautifulSoup(content, 'html.parser')
        img_count = len(soup.find_all('img'))
        
        total_images += img_count
        
        if img_count < 7:
            posts_under_7.append({
                'id': post.get('id', ''),
                'title': post.get('title', '')[:80],
                'count': img_count
            })

    avg_images = total_images / total_posts if total_posts > 0 else 0

    # Generate markdown report
    lines = []
    lines.append("# Image Count Report")
    lines.append("")
    lines.append(f"**Generated:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Total Posts Scanned:** {total_posts}")
    lines.append(f"- **Average Images Per Post:** {avg_images:.1f}")
    lines.append(f"- **Total Posts with Fewer than 7 Images:** {len(posts_under_7)}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Posts with Fewer than 7 Images")
    lines.append("")
    
    if posts_under_7:
        lines.append("| Post ID | Title | Image Count |")
        lines.append("|---------|-------|-------------|")
        for p in posts_under_7:
            lines.append(f"| {p['id']} | {p['title']} | {p['count']} |")
    else:
        lines.append("All posts have 7 or more images. ✅")
    
    lines.append("")
    
    REPORT_PATH.write_text('\n'.join(lines), encoding='utf-8')
    
    # Print summary to terminal
    print(f"Total Posts Scanned: {total_posts}")
    print(f"Average Images Per Post: {avg_images:.1f}")
    print(f"Posts with <7 Images: {len(posts_under_7)}")
    print(f"Report saved to: {REPORT_PATH}")

if __name__ == '__main__':
    main()
