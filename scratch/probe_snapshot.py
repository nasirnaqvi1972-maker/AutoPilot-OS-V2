import json, re
from pathlib import Path
from bs4 import BeautifulSoup

snap = json.loads(Path("content/image_audit_20261020/audit_v2_posts_snapshot.json").read_text(encoding="utf-8"))
print("Posts:", len(snap))
print("Keys:", list(snap[0].keys()))

p = snap[0]
content = p.get("content", "")
print("Title:", p.get("title", "")[:80])
print("Content len:", len(content))
soup = BeautifulSoup(content, "html.parser")
text = soup.get_text(" ", strip=True)
words = len(text.split())
print("Words:", words)

MON_DOMAINS = ["buymeacoffee", "patreon", "gumroad", "ko-fi"]
found = 0
for pp in snap:
    c = pp.get("content", "")
    for link in re.findall(r'href=["\']([^"\']+)', c):
        if any(x in link for x in MON_DOMAINS):
            found += 1
            print("MON:", pp.get("title","")[:50], "|", link[:80])
            break
print("Posts with monetization links:", found)
