p='core/image_curator.py'
s=open(p,encoding='utf-8').read()
old='''                img_url = item.get("urls", {}).get("regular") or item.get("urls", {}).get("full")
                if img_url and img_url not in seen_urls:'''
new='''                alt_l = (alt or "").lower()
                bad = ["stamp", "postage", "monkey", "macaca", "primate", "bee", "insect", "flower"]
                if any(b in alt_l for b in bad):
                    continue
                img_url = item.get("urls", {}).get("regular") or item.get("urls", {}).get("full")
                if img_url and img_url not in seen_urls:'''
assert old in s
s=s.replace(old,new)
open(p,'w',encoding='utf-8').write(s)
print('done')
