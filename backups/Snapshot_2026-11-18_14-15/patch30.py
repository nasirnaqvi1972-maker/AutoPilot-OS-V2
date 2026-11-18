p='safe_batch.py'
s=open(p,encoding='utf-8').read()
old='''    for fig in soup.find_all('figure'):
        fig.decompose()
    for img in soup.find_all('img'):
        img.decompose()'''
new='''    for div in soup.find_all('div', class_='separator'):
        div.decompose()
    for fig in soup.find_all('figure'):
        fig.decompose()
    for img in soup.find_all('img'):
        img.decompose()'''
assert old in s
s=s.replace(old,new)
open(p,'w',encoding='utf-8').write(s)
print('done')
