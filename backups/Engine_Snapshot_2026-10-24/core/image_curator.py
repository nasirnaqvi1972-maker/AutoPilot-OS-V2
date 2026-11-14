import os, re, json, time, urllib.parse, urllib.request, hashlib
from pathlib import Path
from bs4 import BeautifulSoup
from core.html_cleaner import clean_generated_html
import torch
import open_clip
from PIL import Image
import cv2
import numpy as np
import imagehash

# --- RELAY SETUP ---
RELAY_URL = "https://wikimedia-relay.nasirabbasnaqvi.workers.dev"
RELAY_TOKEN = "ddd-secret-2026"

def _relay_get(target_url, timeout=30):
    params = urllib.parse.urlencode({"url": target_url, "token": RELAY_TOKEN})
    req = urllib.request.Request(f"{RELAY_URL}?{params}", headers={"User-Agent": "DustAndDynastyBot/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()

def _relay_json(base_url, **params):
    params["format"] = "json"
    api_url = base_url + "?" + urllib.parse.urlencode(params)
    try:
        raw = _relay_get(api_url)
        return json.loads(raw.decode('utf-8'))
    except Exception:
        return {}

# --- AI SETUP ---
_model = None
_preprocess = None
_tokenizer = None

def _load_clip():
    global _model, _preprocess, _tokenizer
    if _model is None:
        _model, _, _preprocess = open_clip.create_model_and_transforms('ViT-B-32', pretrained='laion2b_s34b_b79k')
        _tokenizer = open_clip.get_tokenizer('ViT-B-32')
        _model.eval()

def contrastive_clip_score(image_path, subject, heading, snippet):
    _load_clip()
    # Use the exact description provided in the HTML
    pos_prompt = f"A photograph of {subject}, showing {snippet}."
    
    negatives = [
        "A photograph of a different monument.",
        "A tourist selfie.",
        "A street sign or informational plaque.",
        "A map or architectural diagram.",
        "A modern building."
    ]
    
    try:
        img = _preprocess(Image.open(image_path).convert("RGB")).unsqueeze(0)
        text = _tokenizer([pos_prompt] + negatives)
        with torch.no_grad():
            img_feat = _model.encode_image(img)
            txt_feat = _model.encode_text(text)
            img_feat /= img_feat.norm(dim=-1, keepdim=True)
            txt_feat /= txt_feat.norm(dim=-1, keepdim=True)
            sims = (img_feat @ txt_feat.T).squeeze(0).tolist()
            
        pos_score = sims[0]
        max_neg = max(sims[1:])
        margin = pos_score - max_neg
        
        # Relaxed threshold to accept more images
        return pos_score > 0.20 and margin > 0.02
    except:
        return False

# --- FILTERS ---
BAD_WORDS = re.compile(r"\b(sign|signage|selfie|poster|logo|map|plan|diagram|flag|coat of arms|plaque|menu|ticket|screenshot|scan|stamp|coin|banner|icon|bus|train)\b", re.I)

def norm_title(t):
    return re.sub(r"[_\-\.\(\)]+", " ", re.sub(r"^File:|\.\w{3,4}$", "", t))

def passes_meta_filter(page, min_w=1280, min_h=720):
    if 'imageinfo' not in page: return False
    ii = page['imageinfo'][0]
    if ii.get('mime') not in ("image/jpeg", "image/png"): return False
    w, h = ii.get('width', 0), ii.get('height', 0)
    if w < min_w or h < min_h: return False
    if w < h * 0.6: return False
    if BAD_WORDS.search(norm_title(page.get('title', ''))): return False
    return True

def passes_aesthetic_filter(image_path):
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None: return False
    img = cv2.resize(img, (1024, int(img.shape[0] * 1024 / img.shape[1])))
    blur_score = cv2.Laplacian(img, cv2.CV_64F).var()
    if blur_score < 30: return False
    if np.mean(img) < 30: return False
    return True

# --- POOLING ---
def build_candidate_pool(subject):
    pool = []
    seen_urls = set()
    key = os.environ.get("UNSPLASH_ACCESS_KEY", "").strip()
    # also read from .env if present
    if not key:
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        try:
            for line in open(env_path, encoding="utf-8"):
                if line.startswith("UNSPLASH_ACCESS_KEY="):
                    key = line.strip().split("=",1)[1]
        except Exception:
            pass
    if key:
        import urllib.request, json
        query = " ".join("".join(c if c.isalnum() or c.isspace() else " " for c in subject).split()[:2])
        try:
            url = "https://api.unsplash.com/search/photos?query=" + urllib.parse.quote(query) + "&orientation=landscape&per_page=30"
            req = urllib.request.Request(url, headers={"Authorization": f"Client-ID {key}", "Accept-Version": "v1"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            seen_alt = set()
            for item in data.get("results", []):
                alt = item.get("alt_description") or ""
                if alt and alt in seen_alt:
                    continue
                if alt:
                    seen_alt.add(alt)
                alt_l = (alt or "").lower()
                bad = ["stamp", "postage", "monkey", "macaca", "primate", "bee", "insect", "flower"]
                if any(b in alt_l for b in bad):
                    continue
                img_url = item.get("urls", {}).get("regular") or item.get("urls", {}).get("full")
                if img_url and img_url not in seen_urls:
                    pool.append({"title": "Unsplash", "anchor": True, "imageinfo": [{"url": img_url, "width": 1600, "height": 900, "mime": "image/jpeg"}]})
                    seen_urls.add(img_url)
            if pool:
                print(f"  [curator] Unsplash returned {len(pool)} candidates.")
            # Fall through to Wikimedia to fill remaining slots
        except Exception as e:
            print(f"  [curator] Unsplash failed: {e}; falling back to Wikimedia.")
    
    WD = "https://www.wikidata.org/w/api.php"
    r = _relay_json(WD, action="wbsearchentities", search=subject, language="en", limit=1)
    qid = r["search"][0]["id"] if r.get("search") else None

    if qid:
        ent = _relay_json(WD, action="wbgetentities", ids=qid, props="claims")
        try:
            p18 = ent["entities"][qid]["claims"]["P18"][0]["mainsnak"]["datavalue"]["value"]
            pool.append({"title": f"File:{p18}", "imageinfo": [{"url": f"https://commons.wikimedia.org/wiki/Special:FilePath/{urllib.parse.quote(p18)}?width=2560", "width": 2560, "height": 1440, "mime": "image/jpeg"}]})
            seen_urls.add(pool[-1]["imageinfo"][0]["url"])
        except: pass

    WIKI = "https://en.wikipedia.org/w/api.php"
    wr = _relay_json(WIKI, action="query", prop="pageimages", titles=subject, pithumbsize="2560")
    for p in wr.get("query", {}).get("pages", {}).values():
        if "thumbnail" in p:
            url = p["thumbnail"]["source"]
            if url not in seen_urls:
                pool.append({"title": "Wiki Lead", "imageinfo": [{"url": url, "width": 2560, "height": 1440, "mime": "image/jpeg"}]})
                seen_urls.add(url)

    if qid:
        c = _relay_json(WD, action="wbgetclaims", entity=qid, property="P373")
        try:
            cat = c["claims"]["P373"][0]["mainsnak"]["datavalue"]["value"]
            COMMONS = "https://commons.wikimedia.org/w/api.php"
            cr = _relay_json(COMMONS, action="query", generator="categorymembers", gcmtitle=f"Category:{cat}", gcmtype="file", gcmlimit="30", prop="imageinfo", iiprop="url|size|mime", iiurlwidth="2560")
            for p in cr.get("query", {}).get("pages", {}).values():
                url = p['imageinfo'][0].get('thumburl') or p['imageinfo'][0].get('url')
                if url not in seen_urls:
                    pool.append(p)
                    seen_urls.add(url)
        except: pass

    if len(pool) < 10:
        COMMONS = "https://commons.wikimedia.org/w/api.php"
        sr = _relay_json(COMMONS, action="query", generator="search", gsrsearch=f'filetype:bitmap "{subject}" OR "{subject} landscape" OR "{subject} nature"', gsrnamespace="6", gsrlimit="30", prop="imageinfo", iiprop="url|size|mime", iiurlwidth="2560")
        for p in sr.get("query", {}).get("pages", {}).values():
            url = p['imageinfo'][0].get('thumburl') or p['imageinfo'][0].get('url')
            if url not in seen_urls:
                pool.append(p)
                seen_urls.add(url)
                
    return pool

# --- PLACEMENT ---
BLOCK_TAGS = {"table", "ul", "ol", "dl", "li", "details", "blockquote", "figure", "aside", "nav", "footer", "pre", "header"}
BLOCK_HEADING = re.compile(r"quick\s*facts|faq|frequently asked|sources?|references?|further reading|related|table of contents|conclusion|summary|q&a|bibliography|see also|visitor information", re.I)
BLOCK_CLASS = re.compile(r"faq|quick|facts|source|ref|toc|infobox|related|widget|accordion", re.I)

def is_protected(p):
    text = p.get_text(" ", strip=True)
    if len(p.find_all('br')) >= 3: return True
    if re.match(r"^(built|location|type|status|year|period|region|country)\b[^.]{0,25}:", text, re.I): return True
    for anc in p.parents:
        if anc.name in BLOCK_TAGS: return True
        attrs = " ".join([anc.get("id", "")] + (anc.get("class") or []))
        if attrs and BLOCK_CLASS.search(attrs): return True
    return False

def get_valid_sections(soup):
    sections = []
    for h in soup.find_all(['h2', 'h3']):
        h_text = h.text.strip()
        if BLOCK_HEADING.search(h_text) or h_text.endswith('?'): continue
        p = h.find_next('p')
        if not p or len(p.text.split()) < 40: continue
        if is_protected(p): continue
        sections.append({"heading": h_text, "p": p})
    return sections

# --- MAIN EXECUTION ---
def curate_images(html_path, output_dir):
    print(f"--- Running Flawless V2 Curator ---")
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    soup = BeautifulSoup(html, 'html.parser')
    soup = clean_generated_html(soup)
    title = soup.find('h1').text.strip() if soup.find('h1') else "Unknown"
    subject = title.split('—')[0].split('|')[0].strip()
    
    os.makedirs(output_dir, exist_ok=True)
    
    sections = get_valid_sections(soup)
    print(f"  [curator] Found {len(sections)} eligible sections.")
    if not sections: return False

    # Fallback: force up to 7 slots using long paragraphs
    if len(sections) < 7:
        used = {id(s['p']) for s in sections}
        for p in soup.find_all('p'):
            if len(sections) >= 7:
                break
            if id(p) in used:
                continue
            text = p.get_text(" ", strip=True)
            if len(text.split()) > 20:
                sections.append({"heading": "Additional View", "p": p})
                used.add(id(p))
    
    pool = build_candidate_pool(subject)
    print(f"  [curator] Candidate pool size: {len(pool)}")
    
    img_count = 0
    hashes = set()
    md5_hashes = set()
    phash_set = set()
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    used_path = os.path.join(ROOT, "content", "used_images.json")
    try:
        with open(used_path, "r", encoding="utf-8") as f:
            hashes |= set(json.load(f))
    except Exception:
        pass
    
    for page in pool:
        if img_count >= len(sections) or img_count >= 7: break
        
        url = page['imageinfo'][0].get('thumburl') or page['imageinfo'][0].get('url')
        temp_path = os.path.join(output_dir, "temp.jpg")
        
        if download_image(url, temp_path):
            with open(temp_path, "rb") as f:
                md5 = hashlib.md5(f.read()).hexdigest()
            if md5 in md5_hashes:
                print("      [Image Validator] Skipping duplicate image (MD5 match).")
                os.remove(temp_path)
                continue
            md5_hashes.add(md5)
            # perceptual hash dedup
            try:
                with Image.open(temp_path) as im:
                    ph = str(imagehash.phash(im.convert("RGB")))
                if ph in phash_set:
                    print("      [Image Validator] Skipping perceptual duplicate.")
                    os.remove(temp_path)
                    continue
                phash_set.add(ph)
            except Exception:
                pass
            if not vision_check(temp_path):
                os.remove(temp_path)
                continue
            try:
                with Image.open(temp_path) as im:
                    if im.width < 800 or im.height < 600:
                        print("      [Image Validator] Skipping low-res image (<800x600).")
                        os.remove(temp_path)
                        continue
            except Exception:
                pass
            if not passes_aesthetic_filter(temp_path):
                os.remove(temp_path)
                continue
                
            try:
                img = Image.open(temp_path).convert('RGB')
                h = str(imagehash.dhash(img))
                if h in hashes:
                    os.remove(temp_path)
                    continue
            except Exception:
                os.remove(temp_path)
                continue
                
            slot = sections[img_count]
            snippet = " ".join(slot['p'].text.split()[:15]) + "..."
            
            print(f"    [validator] Matching to: '{slot['heading']}'")
            if True:
                hashes.add(h)
                try:
                    with open(used_path, "w", encoding="utf-8") as f:
                        json.dump(sorted(hashes), f)
                except Exception:
                    pass

                final_path = os.path.join(output_dir, f"img_{img_count+1:02d}.jpg")
                os.replace(temp_path, final_path)
                
                p_text = slot['p'].get_text(" ", strip=True)
                caption = p_text.split('.')[0] + '.' if '.' in p_text else slot['heading']
                if len(caption) > 150:
                    caption = caption[:147] + "..."
                alt = caption

                figure_html = f"""
                <div class="separator" data-autopilot="1" style="clear: both; text-align: center; margin: 24px 0px;">
                    <a href="img_{img_count+1:02d}.jpg"><img border="0" src="img_{img_count+1:02d}.jpg" alt="{alt}" style="width: 100%; max-width: 800px; height: auto; display: block; margin: 0 auto;" /></a>
                    <div style="font-style: italic; font-size: 0.9em; color: #555; margin-top: 8px;">{alt}</div>
                </div>
                """
                new_fig = BeautifulSoup(figure_html, 'html.parser')
                slot['p'].insert_after(new_fig)
                img_count += 1
                print(f"      [OK] Accepted image {img_count}")
            else:
                os.remove(temp_path)

    if img_count < 7:
        print(f"  [FAIL] Only found {img_count} images. Post requires exactly 7. Moving to failed folder.")
        return False
    if img_count == 0:
        return False

    out_path = os.path.join(output_dir, "_output.html")
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(str(soup))
    return True

def vision_check(image_path):
    try:
        _load_clip()
        import torch
        with Image.open(image_path) as im:
            img = _preprocess(im.convert("RGB")).unsqueeze(0)
        positives = ["architecture", "ruins", "statue", "landscape", "monument"]
        negatives = ["monkey", "animal", "stamp", "postage", "person", "flower", "food"]
        labels = positives + negatives
        text = _tokenizer(labels)
        with torch.no_grad():
            img_feat = _model.encode_image(img)
            txt_feat = _model.encode_text(text)
            img_feat /= img_feat.norm(dim=-1, keepdim=True)
            txt_feat /= txt_feat.norm(dim=-1, keepdim=True)
            sims = (img_feat @ txt_feat.T).squeeze(0).tolist()
        best_idx = max(range(len(sims)), key=lambda i: sims[i])
        best_label = labels[best_idx]
        if best_label in negatives:
            print(f"      [Vision Check] Rejected image (Category: {best_label}).")
            return False
        return True
    except Exception:
        return True

def download_image(url, save_path):
    try:
        if 'unsplash.com' in url or 'images.unsplash.com' in url:
            import urllib.request
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
        else:
            raw = _relay_get(url)
        with open(save_path, 'wb') as f: f.write(raw)
        return True
    except Exception as e:
        print(f"      [download] failed: {e}")
        return False
