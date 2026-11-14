p='core/image_curator.py'
s=open(p,encoding='utf-8').read()
old='def build_candidate_pool(subject):\n    pool = []\n    seen_urls = set()\n'
new='''def build_candidate_pool(subject):
    pool = []
    seen_urls = set()
    key = os.environ.get("UNSPLASH_ACCESS_KEY", "").strip()
    # also read from .env if present
    if not key:
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        try:
            for line in open(env_path, encoding="utf-8"):
                if line.startswith("UNSPLASH_ACCESS_KEY="):
                    key = line.strip().split("=",1)[1]
        except Exception:
            pass
    if key:
        import urllib.request, json
        query = " ".join([w for w in subject.split() if w.lower() not in {"the","a","an","of","and","in"}]) + " high resolution landscape photography"
        try:
            url = "https://api.unsplash.com/search/photos?query=" + urllib.parse.quote(query) + "&orientation=landscape&per_page=10"
            req = urllib.request.Request(url, headers={"Authorization": f"Client-ID {key}", "Accept-Version": "v1"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            seen_alt = set()
            for item in data.get("results", []):
                alt = item.get("alt_description") or ""
                if alt and alt in seen_alt:
                    continue
                if alt:
                    seen_alt.add(alt)
                img_url = item.get("urls", {}).get("regular") or item.get("urls", {}).get("full")
                if img_url and img_url not in seen_urls:
                    pool.append({"title": "Unsplash", "anchor": True, "imageinfo": [{"url": img_url, "width": 1600, "height": 900, "mime": "image/jpeg"}]})
                    seen_urls.add(img_url)
            if pool:
                print(f"  [curator] Unsplash returned {len(pool)} candidates.")
                return pool
        except Exception as e:
            print(f"  [curator] Unsplash failed: {e}; falling back to Wikimedia.")
'''
assert old in s
s=s.replace(old,new)
open(p,'w',encoding='utf-8').write(s)
print('done')
