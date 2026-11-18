p='core/image_curator.py'
s=open(p,encoding='utf-8').read()
old='''            if pool:
                print(f"  [curator] Unsplash returned {len(pool)} candidates.")
'''
new='''            if pool:
                print(f"  [curator] Unsplash returned {len(pool)} candidates.")
            # Fall through to Wikimedia to fill remaining slots
'''
assert old in s
s=s.replace(old,new)
# Remove early return if present
s=s.replace('                print(f"  [curator] Unsplash returned {len(pool)} candidates.")\n                return pool','                print(f"  [curator] Unsplash returned {len(pool)} candidates.")')
open(p,'w',encoding='utf-8').write(s)
print('done')
