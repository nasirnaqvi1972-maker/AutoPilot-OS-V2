p='core/image_curator.py'
s=open(p,encoding='utf-8').read()
s=s.replace('&orientation=landscape&per_page=10','&orientation=landscape&per_page=30')
s=s.replace('query = " ".join([w for w in subject.split() if w.lower() not in {"the","a","an","of","and","in"}]) + " high resolution landscape photography"','query = " ".join(subject.split()[:3])')
old='''            if pool:
                print(f"  [curator] Unsplash returned {len(pool)} candidates.")
                return pool
'''
new='''            if pool:
                print(f"  [curator] Unsplash returned {len(pool)} candidates.")
'''
assert old in s
s=s.replace(old,new)
open(p,'w',encoding='utf-8').write(s)
print('done')
