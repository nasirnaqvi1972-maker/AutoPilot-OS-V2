p='draft_doctor.py'
s=open(p,encoding='utf-8').read()
# add image count check before meta
old='    # meta description'
new='''    imgs = soup.find_all('img')
    if len(imgs) != 7:
        print(f"  [WARNING] Draft has {len(imgs)} images (need 7).")
    # meta description'''
assert old in s
s=s.replace(old,new)
open(p,'w',encoding='utf-8').write(s)
print('done')
