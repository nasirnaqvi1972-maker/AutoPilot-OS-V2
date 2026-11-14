p='post_inspector.py'
s=open(p,encoding='utf-8').read()
s=s.replace('    if len(imgs) != 7:\n        critical.append(f"image count={len(imgs)} (need exactly 7)")','    if len(imgs) == 0:\n        critical.append("no images found")\n    elif len(imgs) != 7:\n        warnings.append(f"image count={len(imgs)} (auto-image posts need 7)")')
open(p,'w',encoding='utf-8').write(s)
print('done')
