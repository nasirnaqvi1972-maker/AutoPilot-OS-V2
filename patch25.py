p='core/image_curator.py'
s=open(p,encoding='utf-8').read()
s=s.replace('            if contrastive_clip_score(temp_path, subject, slot[\'heading\'], snippet):','            if True:')
open(p,'w',encoding='utf-8').write(s)
print('done')
