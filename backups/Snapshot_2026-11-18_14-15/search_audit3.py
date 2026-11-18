import json
import sys

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

with open(r'D:\Projects\AutoPilot_OS_v2\content\image_audit_20261020\audit_v2_posts_snapshot.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Count images per post
print("=== IMAGE COUNTS ===")
posts_under_3 = []
for post in data:
    content = post.get('content', '')
    img_count = content.count('<img')
    if img_count < 3:
        posts_under_3.append((post["title"][:60], img_count, post["id"]))

print(f"Total posts: {len(data)}")
print(f"Posts with < 3 images: {len(posts_under_3)}")
for title, count, pid in posts_under_3:
    print(f'  {title} (ID: {pid}): {count} images')

# Check for monetization links in post content (not sidebar)
print("\n=== MONETIZATION LINKS IN POST BODIES ===")
monetization_domains = ['patreon.com', 'gumroad.com', 'buymeacoffee.com', 'buy me a coffee']
found_monetization = False
for post in data:
    content = post.get('content', '').lower()
    for domain in monetization_domains:
        if domain in content:
            found_monetization = True
            print(f'FOUND in: {post["title"][:80]}')
            print(f'  Domain: {domain}')
            idx = content.find(domain)
            start = max(0, idx-100)
            end = min(len(content), idx+100)
            ctx = content[start:end].encode('ascii', 'ignore').decode('ascii')
            print(f'  Context: ...{ctx}...')
            print()

if not found_monetization:
    print("PASS: No monetization links found in post bodies")

# Check for broken links to deleted posts
print("\n=== BROKEN LINKS TO DELETED POSTS ===")
deleted_urls = [
    'chan-chan-archaeological-zone-city-of.html',
    'agra-fort-red-citadel-of-mughals.html',
    'agra-fort-sandstone-crown-of-yamuna.html'
]
found_broken = False
for post in data:
    content = post.get('content', '')
    for deleted in deleted_urls:
        if deleted in content:
            # Skip if it's the deleted post itself
            if post["id"] in ["307506081574133356", "8839101181469276694"]:
                continue
            found_broken = True
            print(f'FOUND in: {post["title"][:80]}')
            print(f'  Links to deleted: {deleted}')
            print()

if not found_broken:
    print("PASS: No broken links to deleted posts found in other posts")

# Check HTML structure - basic validation
print("\n=== HTML STRUCTURE CHECK ===")
missing_h1 = 0
missing_ld = 0
for post in data:
    content = post.get('content', '')
    has_h1 = '<h1>' in content or '<H1>' in content
    has_ld_json = 'application/ld+json' in content
    if not has_h1:
        missing_h1 += 1
        print(f'MISSING H1: {post["title"][:60]}')
    if not has_ld_json:
        missing_ld += 1
        print(f'MISSING LD+JSON: {post["title"][:60]}')

print(f"Posts missing H1: {missing_h1}")
print(f"Posts missing LD+JSON: {missing_ld}")

# Check image attributions
print("\n=== IMAGE ATTRIBUTION CHECK ===")
no_alt = 0
for post in data:
    content = post.get('content', '')
    # Simple check - count img tags with alt=""
    import re
    img_tags = re.findall(r'<img[^>]*>', content)
    for tag in img_tags:
        if 'alt=""' in tag or 'alt=\'\'' in tag or 'alt=' not in tag:
            no_alt += 1

print(f"Images with missing/empty alt attributes: {no_alt}")

print("\n=== SUMMARY ===")
print(f"Total posts audited: {len(data)}")
print(f"Image minimum (3+) check: {'PASS' if len(posts_under_3) == 0 else 'FAIL'}")
print(f"Monetization links in bodies: {'PASS' if not found_monetization else 'FAIL'}")
print(f"Broken links to deleted posts: {'PASS' if not found_broken else 'FAIL'}")
print(f"HTML structure (H1): {'PASS' if missing_h1 == 0 else 'FAIL'}")
print(f"HTML structure (LD+JSON): {'PASS' if missing_ld == 0 else 'FAIL'}")
print(f"Image attributions: {'PASS' if no_alt == 0 else 'FAIL'}")