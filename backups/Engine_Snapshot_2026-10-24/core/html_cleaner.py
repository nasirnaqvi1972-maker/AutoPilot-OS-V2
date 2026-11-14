from bs4 import BeautifulSoup
import re

KNOWN_HEADERS = [
    'history', 'geography', 'location', 'origins', 'architecture', 'features',
    'purpose', 'construction', 'conservation', 'legacy', 'significance',
    'culture', 'tourism', 'visiting', "visitor's guide", 'how to get there',
    'best time', 'conclusion', 'introduction', 'background', 'context',
    'key features', 'natural features', 'human history', 'modern challenges',
    'enduring legacy', 'related posts', 'frequently asked questions',
    'sources and further reading', 'summary table of facts'
]

def clean_generated_html(soup):
    # Remove text blocks starting with "Image Description:"
    for p in list(soup.find_all('p')):
        try:
            text = p.get_text(strip=True)
            if text.lower().startswith('image description:'):
                p.decompose()
                continue
            if 'image description' in text.lower() and len(text) > 100:
                p.decompose()
                continue
        except Exception:
            continue
    
    # Remove duplicate consecutive paragraphs
    paragraphs = soup.find_all('p')
    to_remove = []
    for i in range(1, len(paragraphs)):
        try:
            prev_text = paragraphs[i-1].get_text(strip=True)
            curr_text = paragraphs[i].get_text(strip=True)
            if prev_text and curr_text and prev_text == curr_text:
                to_remove.append(paragraphs[i])
        except Exception:
            continue
    for p in to_remove:
        try:
            p.decompose()
        except Exception:
            pass
    
    # Upgrade pseudo-headings
    for p in list(soup.find_all('p')):
        try:
            text = p.get_text(strip=True)
            if not text:
                continue
            words = text.split()
            if len(words) < 15 and not text.endswith(('.', '!', '?', ':', ';', ',')):
                lower = text.lower()
                is_header = False
                for kh in KNOWN_HEADERS:
                    if kh in lower:
                        is_header = True
                        break
                if not is_header and len(words) >= 2 and len(words) <= 8:
                    if text.istitle() or all(w and len(w)>0 and w[0].isupper() for w in words if w[0].isalpha()):
                        is_header = True
                if is_header and not p.find_parent(['table', 'ul', 'ol']):
                    h2 = soup.new_tag('h2')
                    h2.string = text
                    p.replace_with(h2)
        except Exception:
            continue
    
    return soup
