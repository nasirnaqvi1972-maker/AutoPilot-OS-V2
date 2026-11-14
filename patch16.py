p='core/image_curator.py'
s=open(p,encoding='utf-8').read()
s=s.replace('            if False and not passes_aesthetic_filter(temp_path):','            if not passes_aesthetic_filter(temp_path):')
s=s.replace('            if True:','            if contrastive_clip_score(temp_path, subject, slot[\'heading\'], snippet):')
s=s.replace('return pos > 0.10 and (pos - max_neg) > 0.01','return pos > 0.22 and (pos - max_neg) > 0.01')
s=s.replace('query = " ".join(subject.split()[:3])','query = " ".join(subject.split()[:3]) + " architecture ruins statue cave"')
# hard fail
s=s.replace('''    if img_count < 7:
        print(f"  [WARNING] Only found {img_count} images total. Post will be published with {img_count} images.")
    if img_count == 0:
        return False''','''    if img_count < 7:
        print(f"  [FAIL] Only found {img_count} images. Post requires exactly 7. Moving to failed folder.")
        return False
    if img_count == 0:
        return False''')
open(p,'w',encoding='utf-8').write(s)
print('done')
