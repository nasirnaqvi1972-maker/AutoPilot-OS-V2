p='core/image_curator.py'
s=open(p,encoding='utf-8').read()
s=s.replace('query = " ".join(subject.split()[:3]) + " architecture ruins statue cave"','query = " ".join("".join(c if c.isalnum() or c.isspace() else " " for c in subject).split()[:2])')
open(p,'w',encoding='utf-8').write(s)
print('done')
