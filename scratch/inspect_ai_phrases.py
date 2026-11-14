import json, re
from pathlib import Path
from bs4 import BeautifulSoup

snap = json.loads(Path("content/image_audit_20261020/audit_v2_posts_snapshot.json").read_text(encoding="utf-8"))

TARGET_IDS = {"2753373518224771616", "4140733200666397033", "29678392317326416"}
AI_RE = re.compile(r'as an ai', re.IGNORECASE)

for p in snap:
    pid = str(p.get("id",""))
    if pid not in TARGET_IDS:
        continue
    soup = BeautifulSoup(p.get("content",""), "html.parser")
    print(f"\n{'='*70}")
    print(f"POST: {p.get('title','')[:70]}")
    print(f"ID  : {pid}")
    # Find all tags containing the phrase
    for tag in soup.find_all(string=AI_RE):
        parent = tag.parent
        # Print surrounding 400 chars
        raw = str(parent)[:400]
        print(f"\n  TAG: <{parent.name}>")
        print(f"  RAW: {raw}")
