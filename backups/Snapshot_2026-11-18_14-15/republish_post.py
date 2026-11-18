import os, sys, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from core.blogger_publisher import get_blogger_service
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
PENDING = ROOT / "content" / "pending"
BLOG_URL = 'https://dustanddynasty.blogspot.com'

def get_service_and_blog():
    service = get_blogger_service()
    blog = service.blogs().getByUrl(url=BLOG_URL).execute()
    return service, blog['id']

def main():
    PENDING.mkdir(parents=True, exist_ok=True)

    post_id = sys.argv[1] if len(sys.argv) > 1 else input("Post ID: ").strip()
    service, blog_id = get_service_and_blog()
    post = service.posts().get(blogId=blog_id, postId=post_id, view="AUTHOR", fetchBody=True).execute()
    title = post.get('title', '')
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:80] + ".html"
    soup = BeautifulSoup(post.get('content', ''), 'html.parser')
    for img in soup.find_all('img'):
        # remove parent figure if exists
        fig = img.find_parent('div', class_='separator')
        if fig:
            fig.decompose()
        else:
            img.decompose()

    out = PENDING / slug
    out.write_text(str(soup), encoding='utf-8')
    print(f"Saved cleaned post to {out}")

    # delete from blogger only after successful save to pending
    try:
        service.posts().delete(blogId=blog_id, postId=post_id).execute()
        print(f"Deleted post {post_id} from Blogger.")
    except Exception as e:
        print(f"[ERROR] Failed to delete post {post_id} from Blogger: {e}")
        print(f"  Post has been saved to pending at {out} — please delete manually from Blogger.")

if __name__ == "__main__":
    main()
