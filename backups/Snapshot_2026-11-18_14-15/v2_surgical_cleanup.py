import json
import re
import time
from pathlib import Path
from bs4 import BeautifulSoup
from core.blogger_publisher import get_blogger_service

PROJECT_ROOT = Path(r"D:\Projects\AutoPilot_OS_v2")
DRY_RUN = True

TARGETS = ["visitor's guide", "summary table", "frequently asked questions", "faq",
           "enduring legacy", "human connection", "purpose and lifestyle"]

BACKUP_DIR = PROJECT_ROOT / "backups"
BACKUP_DIR.mkdir(exist_ok=True)
PREVIEW_DIR = PROJECT_ROOT / "offline_previews"
PREVIEW_DIR.mkdir(exist_ok=True)


def norm(t):
    return re.sub(r"\s+", " ", t).strip().lower()


def cleanup_html(html):
    soup = BeautifulSoup(html, "html.parser")
    body = soup.body if soup.body else soup
    removed = 0
    headings = list(body.find_all(["h2", "h3"]))
    for h in headings:
        if norm(h.get_text()) in TARGETS:
            removed += 1
            sib = h.next_sibling
            to_remove = [h]
            while sib is not None:
                if getattr(sib, "name", None) in ("h2", "h3"):
                    break
                to_remove.append(sib)
                sib = sib.next_sibling
            for el in to_remove:
                el.extract()
    return str(soup), removed


def main():
    service = get_blogger_service()
    blog = service.blogs().getByUrl(url="https://dustanddynasty.blogspot.com").execute()
    blog_id = blog["id"]

    inv = json.loads((PROJECT_ROOT / "verified_inventory.json").read_text(encoding="utf-8"))
    posts = inv["posts"]

    total_blocks = 0
    changed = 0
    affected_titles = []
    for post_id, meta in posts.items():
        try:
            live = service.posts().get(blogId=blog_id, postId=post_id, fields="id,content,title").execute()
        except Exception as e:
            print(f"[ERR] {post_id}: {e}")
            continue
        content = live.get("content", "")
        new_html, removed = cleanup_html(content)
        if removed:
            total_blocks += removed
            changed += 1
            title = live.get("title", meta.get("title", ""))
            affected_titles.append(title)
            print(f"[{post_id}] {title} -> removed {removed} block(s)")
            if DRY_RUN:
                (PREVIEW_DIR / f"{post_id}_cleaned.html").write_text(new_html, encoding="utf-8")
            if not DRY_RUN and new_html != content:
                (BACKUP_DIR / f"{post_id}_original.html").write_text(content, encoding="utf-8")
                service.posts().patch(blogId=blog_id, postId=post_id, body={"content": new_html}).execute()
                time.sleep(2)

    print("\nAffected post titles:")
    for t in affected_titles:
        print(f"  - {t}")

    print(f"\nTotal posts with template blocks: {changed}")
    print(f"Total template blocks removed: {total_blocks}")
    print(f"DRY_RUN = {DRY_RUN}")


if __name__ == "__main__":
    main()
