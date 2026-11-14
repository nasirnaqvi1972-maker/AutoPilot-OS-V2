p='core/image_curator.py'
s=open(p,encoding='utf-8').read()
old='''def download_image(url, save_path):
    try:
        raw = _relay_get(url)
        with open(save_path, 'wb') as f: f.write(raw)
        return True
    except: return False
'''
new='''def download_image(url, save_path):
    try:
        if 'unsplash.com' in url or 'images.unsplash.com' in url:
            import urllib.request
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
        else:
            raw = _relay_get(url)
        with open(save_path, 'wb') as f: f.write(raw)
        return True
    except Exception as e:
        print(f"      [download] failed: {e}")
        return False
'''
assert old in s
s=s.replace(old,new)
open(p,'w',encoding='utf-8').write(s)
print('done')
