from bs4 import BeautifulSoup
from core.section_finder import find_sections
with open('content/failed/wood-buffalo.html', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')
secs = find_sections(soup)
print('FAIL', len(secs))
