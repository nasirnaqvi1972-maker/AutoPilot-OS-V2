p='core/image_curator.py'
s=open(p,encoding='utf-8').read()
old='''    img_count = 0
    hashes = set()
'''
new='''    img_count = 0
    hashes = set()
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    used_path = os.path.join(ROOT, "content", "used_images.json")
    try:
        with open(used_path, "r", encoding="utf-8") as f:
            hashes |= set(json.load(f))
    except Exception:
        pass
'''
assert old in s
s=s.replace(old,new)
old2='                hashes.add(h)'
new2='''                hashes.add(h)
                try:
                    with open(used_path, "w", encoding="utf-8") as f:
                        json.dump(sorted(hashes), f)
                except Exception:
                    pass
'''
assert old2 in s
s=s.replace(old2,new2)
# ensure json import
if 'import json' not in s:
    s = s.replace('import os, re', 'import os, re, json')
open(p,'w',encoding='utf-8').write(s)
print('done')
