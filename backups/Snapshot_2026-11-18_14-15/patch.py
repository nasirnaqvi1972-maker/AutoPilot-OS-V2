import re
p='core/image_curator.py'
s=open(p,encoding='utf-8').read()
s=s.replace('from bs4 import BeautifulSoup','from bs4 import BeautifulSoup\nfrom core.html_cleaner import clean_generated_html')
old="    soup = BeautifulSoup(html, 'html.parser')\n"
new="    soup = BeautifulSoup(html, 'html.parser')\n    soup = clean_generated_html(soup)\n"
assert old in s
s=s.replace(old,new)
s=s.replace('\u274c','[FAIL]').replace('\u2705','[OK]')
open(p,'w',encoding='utf-8').write(s)
print('done')
