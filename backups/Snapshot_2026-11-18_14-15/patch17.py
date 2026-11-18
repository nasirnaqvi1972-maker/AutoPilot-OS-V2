p='post_inspector.py'
s=open(p,encoding='utf-8').read()
s=s.replace('    if len(imgs) != 7:\n        warnings.append(f"image count={len(imgs)} (need 7)")','    if len(imgs) != 7:\n        critical.append(f"image count={len(imgs)} (need exactly 7)")')
open(p,'w',encoding='utf-8').write(s)
print('done')
