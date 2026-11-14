p='core/image_curator.py'
s=open(p,encoding='utf-8').read()
s=s.replace('            if h in hashes: continue','            if h in hashes:\n                print("      [Image Validator] Skipping duplicate image within post.")\n                continue')
open(p,'w',encoding='utf-8').write(s)
print('done')
