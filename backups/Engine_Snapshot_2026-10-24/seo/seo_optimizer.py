import re
import json
from bs4 import BeautifulSoup

class SEOOptimizer:
    def __init__(self, html_content):
        self.soup = BeautifulSoup(html_content, 'html.parser')

    def clean_headings(self):
        """Ensures exactly ONE <h1> (the title) and demotes any rogue <h1> in the body to <h2>."""
        h1_tags = self.soup.find_all('h1')
        if len(h1_tags) > 1:
            for h1 in h1_tags[1:]:
                h1.name = 'h2' # Demote to H2
        return self

    def inject_schema_markup(self, title, author="Nasir A Naqvi"):
        """Injects JSON-LD schema for Google Rich Results."""
        # Remove existing schema if any
        for script in self.soup.find_all('script', type='application/ld+json'):
            script.decompose()

        schema = {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": title,
            "author": {
                "@type": "Person",
                "name": author
            }
        }
        
        script_tag = self.soup.new_tag('script')
        script_tag['type'] = 'application/ld+json'
        script_tag.string = json.dumps(schema, indent=4)
        self.soup.insert(0, script_tag)
        return self

    def get_meta_description(self):
        """Extracts the first 150 characters of the first paragraph for Google."""
        p = self.soup.find('p')
        if p:
            text = p.get_text(strip=True)
            return text[:150] + "..." if len(text) > 150 else text
        return ""

    def optimize_images(self):
        """Adds lazy loading and dimensions to prevent layout shift."""
        for img in self.soup.find_all('img'):
            img['loading'] = 'lazy'
            if not img.get('width') and not img.get('height'):
                img['width'] = '1280'
                img['height'] = '720' # Fallback aspect ratio
        return self

    def get_html(self):
        return str(self.soup)
