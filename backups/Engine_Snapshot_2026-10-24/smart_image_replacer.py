import os, sys, json, re, hashlib, urllib.request, tempfile
from pathlib import Path
sys.path.insert(0, r"D:\Projects\AutoPilot_OS_v2")
from core.blogger_publisher import get_blogger_service
from bs4 import BeautifulSoup
import torch, open_clip
from PIL import Image

post_id = sys.argv[1] if len(sys.argv) > 1 else input("Post ID: ").strip()
service = get_blogger_service()
blog = service.blogs().getByUrl(url='https://dustanddynasty.blogspot.com').execute()
blog_id = blog['id']
post = service.posts().get(blogId=blog_id, postId=post_id, view="AUTHOR", fetchBody=True).execute()
title = post.get('title','')
html = post.get('content','')
soup = BeautifulSoup(html, 'html.parser')

# Unsplash candidates
key = os.environ.get("UNSPLASH_ACCESS_KEY", "")
if not key:
    for line in open(r"D:\Projects\AutoPilot_OS_v2\.env", encoding="utf-8"):
        if line.startswith("UNSPLASH_ACCESS_KEY="):
            key = line.strip().split("=",1)[1]
query = " ".join(title.split()[:3])
url = "https://api.unsplash.com/search/photos?query=" + urllib.parse.quote(query) + "&orientation=landscape&per_page=30"
req = urllib.request.Request(url, headers={"Authorization": f"Client-ID {key}", "Accept-Version": "v1"})
with urllib.request.urlopen(req, timeout=20) as resp:
    data = json.loads(resp.read().decode("utf-8"))

candidates = []
for item in data.get("results", []):
    img_url = item.get("urls", {}).get("regular")
    if img_url:
        candidates.append(img_url)

# Download candidates
tmpdir = tempfile.mkdtemp()
cand_paths = []
cand_md5 = []
for i, u in enumerate(candidates):
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
        md5 = hashlib.md5(raw).hexdigest()
        if md5 in cand_md5:
            continue
        cand_md5.append(md5)
        p = os.path.join(tmpdir, f"cand_{i}.jpg")
        open(p, "wb").write(raw)
        cand_paths.append((p, u))
    except Exception:
        pass

# CLIP
model, _, preprocess = open_clip.create_model_and_transforms('ViT-B-32', pretrained='laion2b_s34b_b79k')
tokenizer = open_clip.get_tokenizer('ViT-B-32')
model.eval()

def clip_score(img_path, text):
    try:
        with Image.open(img_path) as im:
            img = preprocess(im.convert("RGB")).unsqueeze(0)
        with torch.no_grad():
            img_feat = model.encode_image(img)
            txt = tokenizer([text])
            txt_feat = model.encode_text(txt)
            img_feat /= img_feat.norm(dim=-1, keepdim=True)
            txt_feat /= txt_feat.norm(dim=-1, keepdim=True)
            return float((img_feat @ txt_feat.T).item())
    except Exception:
        return 0.0

used_md5 = set()
for img_tag in soup.find_all("img"):
    # find preceding p
    prev = img_tag.find_previous("p")
    text = prev.get_text(" ", strip=True) if prev else title
    text = text[:100]
    best_score = -1
    best_url = None
    best_md5 = None
    for pth, u in cand_paths:
        md5 = hashlib.md5(open(pth, "rb").read()).hexdigest()
        if md5 in used_md5:
            continue
        score = clip_score(pth, text)
        if score > best_score:
            best_score = score
            best_url = u
            best_md5 = md5
    if best_url:
        used_md5.add(best_md5)
        img_tag["src"] = best_url
        print(f'[SmartMatch] Placed image for block "{text[:40]}..." with confidence score: {best_score:.2f}')

# patch
body = {'id': post_id, 'title': title, 'content': str(soup)}
if post.get('searchDescription'):
    body['searchDescription'] = post['searchDescription']
if post.get('labels'):
    body['labels'] = post['labels']
service.posts().patch(blogId=blog_id, postId=post_id, body=body).execute()
print("Post updated.")
