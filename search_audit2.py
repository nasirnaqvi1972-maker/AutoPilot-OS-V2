import json

with open(r'D:\Projects\AutoPilot_OS_v2\content\image_audit_20261020\audit_v2_posts_snapshot.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Count images per post
print("=== IMAGE COUNTS ===")
posts_under_3 = []
for post in data:
    content = post.get('content', '')
    # Count img tags
    img_count = content.count('<img')
    if img_count < 3:
        posts_under_3.append((post["title"][:60], img_count, post["id"]))
    print(f'{post["title"][:60]}: {img_count} images')

print(f"\nPosts with < 3 images: {len(posts_under_3)}")
for title, count, pid in posts_under_3:
    print(f'  {title} (ID: {pid}): {count} images')

# Check for monetization links in post content (not sidebar)
print("\n=== MONETIZATION LINKS IN POST BODIES ===")
monetization_domains = ['patreon.com', 'gumroad.com', 'buymeacoffee.com', 'buy me a coffee']
for post in data:
    content = post.get('content', '').lower()
    for domain in monetization_domains:
        if domain in content:
            print(f'FOUND in: {post["title"][:80]}')
            print(f'  Domain: {domain}')
            idx = content.find(domain)
            start = max(0, idx-100)
            end = min(len(content), idx+100)
            ctx = content[start:end].encode('ascii', 'ignore').decode('ascii')
            print(f'  Context: ...{ctx}...')
            print()

# Check for broken links to deleted posts
print("=== BROKEN LINKS TO DELETED POSTS ===")
deleted_urls = [
    'chan-chan-archaeological-zone-city-of.html',
    'agra-fort-red-citadel-of-mughals.html',
    'agra-fort-sandstone-crown-of-yamuna.html'
]
for post in data:
    content = post.get('content', '')
    for deleted in deleted_urls:
        if deleted in content:
            print(f'FOUND in: {post["title"][:80]}')
            print(f'  Links to deleted: {deleted}')
            print()

# Check HTML structure - basic validation
print("=== HTML STRUCTURE CHECK ===")
for post in data:
    content = post.get('content', '')
    has_h1 = '<h1>' in content or '<H1>' in content
    has_ld_json = 'application/ld+json' in content
    if not has_h1:
        print(f'MISSING H1: {post["title"][:60]}')
    if not has_ld_json:
        print(f'MISSING LD+JSON: {post["title"][:60]}')

print("\nDone.")