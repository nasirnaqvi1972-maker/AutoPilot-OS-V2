p='core/image_curator.py'
s=open(p,encoding='utf-8').read()
old='''    if img_count == 0:
        return False
'''
new='''    if img_count < 7:
        print(f"  [WARNING] Only found {img_count} images total. Post will be published with {img_count} images.")
    if img_count == 0:
        return False
'''
assert old in s
s=s.replace(old,new)
open(p,'w',encoding='utf-8').write(s)
print('done')
