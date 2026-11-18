import json

with open(r'D:\Projects\AutoPilot_OS_v2\content\image_audit_20261020\audit_v2_posts_snapshot.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Search for restricted words in content
restricted_words = ['dead', 'nazi', 'war', 'opium', 'kill']
for post in data:
    content = post.get('content', '').lower()
    for word in restricted_words:
        if word in content:
            print(f'POST: {post["title"][:80]}')
            print(f'  WORD: {word}')
            idx = content.find(word)
            start = max(0, idx-150)
            end = min(len(content), idx+150)
            ctx = content[start:end].encode('ascii', 'ignore').decode('ascii')
            print(f'  CONTEXT: ...{ctx}...')
            print()

# Count images per post
print("\n=== IMAGE COUNTS ===")
for post in data:
    content = post.get('content', '')
    # Count img tags
    img_count = content.count('<img')
    print(f'{post["title"][:60]}: {img_count} images')