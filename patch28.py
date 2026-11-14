p='safe_batch.py'
s=open(p,encoding='utf-8').read()
old='''    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
        
    soup = BeautifulSoup(html_content, 'html.parser')
    h1 = soup.find('h1')'''
new='''    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
        
    soup = BeautifulSoup(html_content, 'html.parser')
    for fig in soup.find_all('figure'):
        fig.decompose()
    for img in soup.find_all('img'):
        img.decompose()
    print("  [Engine] Removed old images from HTML. Ready for fresh fetch.")
    html_content = str(soup)
    h1 = soup.find('h1')'''
assert old in s
s=s.replace(old,new)
open(p,'w',encoding='utf-8').write(s)
print('done')
