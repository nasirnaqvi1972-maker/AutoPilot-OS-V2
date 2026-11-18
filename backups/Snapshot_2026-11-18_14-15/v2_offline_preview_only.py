import os
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
from core.blogger_publisher import get_blogger_service

ROOT = Path(r"D:\Projects\AutoPilot_OS_v2")
INVENTORY_PATH = ROOT / "verified_inventory.json"
DRAFTS_DIR = ROOT / "drafts"
OUTPUT_DIR = ROOT / "offline_previews" 

def clean_draft_html(raw_html: str) -> str:
    # 1. Strip internal QA Fact-Check Report
    raw_html = re.split(r'(?i)fact-check report|###\s*5\.|---\s*##\s*5\.', raw_html)[0]
    
    soup = BeautifulSoup(raw_html, "html.parser")
    
    # 2. COMPLETELY REMOVE all heading tags (h1 to h6) and their text
    for h in soup.find_all(re.compile(r"^h[1-6]$")):
        h.decompose()
                
    cleaned_text = str(soup)
    cleaned_text = re.sub(r'[-—_\s]{3,}$', '', cleaned_text).strip()
    return cleaned_text

def extract_images(original_html):
    soup = BeautifulSoup(original_html, "html.parser")
    images = []
    
    # Extract ONLY the <img> tag, ignoring old <figure> or <div> captions that cause duplication
    for img in soup.find_all("img"):
        # Skip tiny icons or spacer images
        if img.get("width") and str(img.get("width")).isdigit() and int(img.get("width")) < 50: continue
        if img.get("height") and str(img.get("height")).isdigit() and int(img.get("height")) < 50: continue
        
        img_html = str(img)
        images.append(f"<div style='text-align: center; margin: 30px 0;'>{img_html}</div>")
        
    return images

def inject_images_evenly(html_text, images):
    if not images: return html_text
    soup = BeautifulSoup(html_text, "html.parser")
    
    # Insert after paragraphs
    blocks = soup.find_all(['p', 'ul', 'ol']) 
    if not blocks:
        for img in images:
            soup.append(BeautifulSoup(img, "html.parser"))
        return str(soup)

    step = max(1, len(blocks) // (len(images) + 1))
    img_idx = 0
    for i, block in enumerate(blocks):
        if img_idx >= len(images): break
        if (i + 1) % step == 0:
            block.insert_after(BeautifulSoup(images[img_idx], "html.parser"))
            img_idx += 1
            
    while img_idx < len(images):
        soup.append(BeautifulSoup(images[img_idx], "html.parser"))
        img_idx += 1
    return str(soup)

def generate_footer_html(site_title):
    clean_title = site_title.split('—')[0].split('|')[0].strip()
    map_query = clean_title.replace(' ', '+')
    
    custom_banner = """
    <!--Start of Dust and Dynasty Sidebar Support Banner-->
    <div class="sidebar-support-banner">
    <h3>🌍 Support Dust and Dynasty</h3>
    <p>Your support funds the research and hosting that keeps this encyclopedia free for everyone.</p>
    <div class="sidebar-button-group">
    <a class="sidebar-btn sidebar-btn-one-time" href="https://dustanddynasty.gumroad.com/l/coffee" rel="noopener" target="_blank">☕ Buy Me a Coffee</a>
    <a class="sidebar-btn sidebar-btn-monthly" href="https://www.patreon.com/cw/dustanddynasty" rel="noopener" target="_blank">🔁 Monthly Support</a>
    </div>
    </div>
    <style>
      .sidebar-support-banner {
        background-color: #FDFBF7; 
        border: 1px solid #E6DBCB; 
        border-radius: 8px;
        padding: 15px;
        text-align: center;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        margin-top: 40px;
        margin-bottom: 20px;
      }
      .sidebar-support-banner h3 { color: #2C3E50; margin-top: 0; margin-bottom: 10px; font-size: 16px; }
      .sidebar-support-banner p { color: #5A6C7A; margin-bottom: 15px; font-size: 13px; line-height: 1.4; }
      .sidebar-button-group { display: flex; flex-direction: column; gap: 10px; }
      .sidebar-btn { display: block; padding: 10px 15px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 14px; transition: background-color 0.3s ease; text-align: center; }
      .sidebar-btn-one-time { background-color: #D4A373; color: #FFFFFF; }
      .sidebar-btn-one-time:hover { background-color: #C39262; }
      .sidebar-btn-monthly { background-color: #2A5C43; color: #FFFFFF; }
      .sidebar-btn-monthly:hover { background-color: #1E422F; }
    </style>
    <!--End of Dust and Dynasty Sidebar Support Banner-->
    """

    footer = f"""
    <hr style="margin: 40px 0;" />
    
    <p><strong>Location Map</strong></p>
    <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 8px; margin-bottom: 40px;">
        <iframe 
            src="https://maps.google.com/maps?q={map_query}&t=&z=10&ie=UTF8&iwloc=&output=embed" 
            style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 0;" 
            allowfullscreen="" 
            loading="lazy">
        </iframe>
    </div>
    
    {custom_banner}
    """
    return footer

def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    print("Fetching live posts (READ ONLY) to get original images...")
    service = get_blogger_service()
    blog = service.blogs().getByUrl(url='https://dustanddynasty.blogspot.com').execute()
    blog_id = str(blog['id'])
    
    data = json.loads(INVENTORY_PATH.read_text(encoding="utf-8-sig"))
    inventory = data.get("posts", {})

    draft_paths = list(DRAFTS_DIR.glob("*_revision.html"))
    
    for draft_path in draft_paths:
        stem = draft_path.stem.replace("_revision", "")
        
        matched_id = None
        matched_title = ""
        for pid, item in inventory.items():
            safe_name = re.sub(r'[^a-zA-Z0-9]', '_', item["title"])[:30].lower()
            if safe_name == stem or (len(stem) > 3 and stem in safe_name):
                matched_id = pid
                matched_title = item["title"]
                break
                
        if not matched_id:
            print(f"Skipping {draft_path.name} (No match)")
            continue
            
        print(f"Creating offline preview for: {draft_path.name}")
        
        original_post = service.posts().get(blogId=blog_id, postId=matched_id).execute()
        original_html = original_post.get("content", "")
        
        original_images = extract_images(original_html)
        new_text = clean_draft_html(draft_path.read_text(encoding="utf-8"))
        
        combined_html = inject_images_evenly(new_text, original_images)
        
        footer_html = generate_footer_html(matched_title)
        final_html = combined_html + "\n" + footer_html
        
        out_file = OUTPUT_DIR / f"{matched_id}_preview.html"
        out_file.write_text(final_html, encoding="utf-8")
        print(f"  -> Saved to {out_file.name}")

    print("\nDONE. No live posts were modified.")
    print(f"Open the folder 'offline_previews' to review the HTML files.")

if __name__ == "__main__":
    main()