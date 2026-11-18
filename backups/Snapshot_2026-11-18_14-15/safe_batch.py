import os
import re
import json
import csv
import sys
import shutil
import tempfile
import datetime
import subprocess
import traceback
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from bs4 import BeautifulSoup

sys.path.append(str(Path(__file__).resolve().parent))
from core.blogger_publisher import publish_post, get_blogger_service
from core.image_curator import curate_images
from location_detector import detect_location
from topic_tracker import main as run_topic_tracker

V2_ROOT = Path(__file__).resolve().parent
PENDING_DIR = V2_ROOT / "content" / "pending"
REGISTRY_PATH = V2_ROOT / "content" / "post_registry.json"

# Fallback to data/post_registry.json if content/ doesn't exist yet
if not REGISTRY_PATH.exists() and (V2_ROOT / "data" / "post_registry.json").exists():
    REGISTRY_PATH = V2_ROOT / "data" / "post_registry.json"

# Load the registry (memory)
if REGISTRY_PATH.exists():
    with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
        registry = json.load(f)
else:
    registry = {}
PROCESSED_DIR = V2_ROOT / "content" / "processed"
FAILED_DIR = V2_ROOT / "content" / "failed"

def update_registry_atomic(post_id: str, title: str, doc_name: str):
    """Atomically updates content/post_registry.json with new post entry (STA-03)."""
    target_registry_path = V2_ROOT / "content" / "post_registry.json"
    target_registry_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        current_registry = {}
        if target_registry_path.exists():
            with open(target_registry_path, 'r', encoding='utf-8') as f:
                current_registry = json.load(f)
        elif (V2_ROOT / "data" / "post_registry.json").exists():
            with open(V2_ROOT / "data" / "post_registry.json", 'r', encoding='utf-8') as f:
                current_registry = json.load(f)

        entry = {
            "post_id": post_id,
            "title": title,
            "published_at": datetime.datetime.now().isoformat(),
            "file": doc_name
        }
        current_registry[doc_name] = entry
        slug = re.sub(r'[^a-zA-Z0-9]+', '-', title.lower()).strip('-')
        current_registry[slug] = entry

        fd, tmp_path_str = tempfile.mkstemp(dir=str(target_registry_path.parent), prefix=".tmp_registry_", suffix=".json")
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(current_registry, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path_str, str(target_registry_path))
        print(f"  [Registry] Atomically updated {target_registry_path.name} with post ID {post_id}.")
    except Exception as e:
        print(f"  [Registry Error] Failed to update post registry: {e}")


def remove_site_from_master_list(title: str):
    """Remove a site from sites.csv after successful publication to prevent duplicates."""
    target = unicodedata.normalize('NFC', title.strip().lower())
    sites_path = V2_ROOT / "sites.csv"

    if not sites_path.exists():
        print(f"  [Master List] sites.csv not found at {sites_path}")
        return

    rows = []
    removed = False
    fieldnames = None
    with open(sites_path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            site_name = row.get('site_name', '')
            if unicodedata.normalize('NFC', site_name.strip().lower()) == target and not removed:
                removed = True
                print(f"  [Master List] Removing '{title}' from sites.csv")
                continue
            rows.append(row)

    if not removed:
        print(f"  [Master List] '{title}' not found in sites.csv. No removal needed.")
        return

    fd, tmp_path_str = tempfile.mkstemp(dir=str(sites_path.parent), prefix=".tmp_sites_", suffix=".csv")
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(tmp_path_str, str(sites_path))
        print(f"[Master List] Removed '{title}' from sites.csv to prevent duplicates.")
    except Exception:
        if os.path.exists(tmp_path_str):
            os.unlink(tmp_path_str)
        raise

def convert_docx_to_html(docx_path: Path) -> Path:
    """Converts a .docx file in pending/ to an equivalent .html file."""
    html_path = docx_path.with_suffix(".html")
    try:
        with zipfile.ZipFile(str(docx_path)) as z:
            xml_content = z.read("word/document.xml")
        tree = ET.fromstring(xml_content)
        namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        html_parts = []
        for p in tree.iterfind(".//w:p", namespaces):
            texts = [t.text for t in p.iterfind(".//w:t", namespaces) if t.text]
            if texts:
                p_text = "".join(texts).strip()
                if p_text:
                    pStyle = p.find(".//w:pPr/w:pStyle", namespaces)
                    val = pStyle.attrib.get(f"{{{namespaces['w']}}}val", "") if pStyle is not None else ""
                    if "Heading1" in val or "Title" in val:
                        html_parts.append(f"<h1>{p_text}</h1>")
                    elif "Heading" in val:
                        html_parts.append(f"<h2>{p_text}</h2>")
                    else:
                        html_parts.append(f"<p>{p_text}</p>")
        converted_html = "\n".join(html_parts)
        html_path.write_text(converted_html, encoding="utf-8")
        safe_atomic_move(docx_path, PROCESSED_DIR)
        print(f"  [DOCX Converter] Converted {docx_path.name} -> {html_path.name}")
        return html_path
    except Exception as e:
        print(f"  [DOCX Converter] Failed to convert {docx_path.name}: {e}")
        return None

def safe_atomic_move(src_path: Path, dst_dir: Path):
    """Atomically moves a file to dst_dir using tempfile -> os.replace -> unlink (STA-02)."""
    src = Path(src_path)
    dst_dir = Path(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst_final = dst_dir / src.name

    # Create temporary file in destination folder to ensure same filesystem volume
    fd, tmp_path_str = tempfile.mkstemp(dir=str(dst_dir), prefix=f".tmp_{src.stem}_", suffix=src.suffix)
    os.close(fd)
    tmp_path = Path(tmp_path_str)

    try:
        shutil.copy2(str(src), str(tmp_path))
        os.replace(str(tmp_path), str(dst_final))
        src.unlink()
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise

def process_post(html_path):
    print(f"\n==================================================")
    print(f"PROCESSING: {html_path.name}")
    print(f"==================================================")

    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, 'html.parser')
    h1 = soup.find('h1')
    title = h1.get_text(strip=True) if h1 else re.sub(r'[-_]+', ' ', html_path.stem).title()
    print(f"  [main] Title: {title}")

    img_folder = PROCESSED_DIR / html_path.stem

    # Check if post already contains images BEFORE stripping
    existing_imgs = soup.find_all("img")
    if len(existing_imgs) >= 1:
        print(f"  [Engine] Post already contains {len(existing_imgs)} images. Skipping Auto-Image fetching.")
        # Strip old separator divs and figures but keep img tags
        for div in soup.find_all('div', class_='separator'):
            div.decompose()
        for fig in soup.find_all('figure'):
            fig.decompose()
        html_content = str(soup)
        success = True
        # ensure img_folder exists
        img_folder.mkdir(parents=True, exist_ok=True)
        # copy html to curated output
        curated_html_path = img_folder / "_output.html"
        curated_html_path.write_text(html_content, encoding="utf-8")
    else:
        print("  [Engine] No images found. Fetching images via curator...")
        try:
            # curate_images reads the original file from disk and adds images
            success = curate_images(html_path, img_folder)
        except Exception as e:
            print(f"  [FAIL] Curator crashed: {e}")
            traceback.print_exc()
            success = False

    if not success:
        print("  [FAIL] Curator failed to place images. Moving to failed.")
        safe_atomic_move(html_path, FAILED_DIR)
        return
        
    curated_html_path = img_folder / "_output.html"
    if not curated_html_path.exists():
         print("  [FAIL] Curated HTML not found. Moving to failed.")
         safe_atomic_move(html_path, FAILED_DIR)
         return
         
    print(f"\n--- Publishing to Blogger ---")
    # Check for existing post (draft or live) with same title
    existing_id = None
    try:
        service = get_blogger_service()
        blog = service.blogs().getByUrl(url='https://dustanddynasty.blogspot.com').execute()
        blog_id = blog['id']
        target_title = unicodedata.normalize('NFC', title.strip().lower())
        page_token = None
        while True:
            res = service.posts().list(blogId=blog_id, maxResults=100, pageToken=page_token).execute()
            for d in res.get('items', []):
                d_title = unicodedata.normalize('NFC', d.get('title', '').strip().lower())
                if d_title == target_title:
                    existing_id = d['id']
                    break
            if existing_id:
                break
            page_token = res.get('nextPageToken')
            if not page_token:
                break
    except Exception as e:
        print(f"  [post check] failed: {e}")
    if existing_id:
        print(f"  [Engine] UPDATED existing draft (ID: {existing_id}) in place. No duplicates created.")
    else:
        print("  [Engine] CREATED new draft.")

    labels = detect_location(title, html_content)
    print(f"  [Engine] Assigned labels: {', '.join(labels) if labels else 'none'}.")

    post_id = publish_post(
        html_path=curated_html_path,
        img_folder=img_folder,
        title=title,
        labels=labels,
        post_id=existing_id
    )
    
    if post_id:
        print(f"[AutoPilot] Post published (ID: {post_id}). Running post-publish fixers...")
        LOGS_DIR = V2_ROOT / "logs"
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        failure_log = LOGS_DIR / "fixer_failures.log"
        
        # Smart Image Replacer (Fail-soft)
        try:
            res_smart = subprocess.run(
                [str(Path(__file__).resolve().parent / "os_env" / "Scripts" / "python.exe"),
                 str(Path(__file__).resolve().parent / "smart_image_replacer.py"), str(post_id)],
                cwd=str(Path(__file__).resolve().parent),
                timeout=120,
                capture_output=True,
                text=True
            )
            if res_smart.returncode != 0:
                print(f"  [smart] Finished with non-zero exit code ({res_smart.returncode}). Logged to fixer_failures.log.")
                with open(failure_log, "a", encoding="utf-8") as fl:
                    fl.write(f"[{datetime.datetime.now().isoformat()}] smart_image_replacer failed on post {post_id} (code {res_smart.returncode}):\n{res_smart.stderr}\n")
        except Exception as e:
            print(f"  [smart] Exception: {e}. Logged.")
            with open(failure_log, "a", encoding="utf-8") as fl:
                fl.write(f"[{datetime.datetime.now().isoformat()}] smart_image_replacer exception on post {post_id}: {e}\n")

        # Draft Doctor (Fail-soft)
        try:
            res_doc = subprocess.run(
                [str(Path(__file__).resolve().parent / "os_env" / "Scripts" / "python.exe"),
                 str(Path(__file__).resolve().parent / "draft_doctor.py"), str(post_id)],
                cwd=str(Path(__file__).resolve().parent),
                timeout=120,
                capture_output=True,
                text=True
            )
            if res_doc.returncode != 0:
                print(f"  [doctor] Finished with non-zero exit code ({res_doc.returncode}). Logged to fixer_failures.log.")
                with open(failure_log, "a", encoding="utf-8") as fl:
                    fl.write(f"[{datetime.datetime.now().isoformat()}] draft_doctor failed on post {post_id} (code {res_doc.returncode}):\n{res_doc.stderr}\n")
        except Exception as e:
            print(f"  [doctor] Exception: {e}. Logged.")
            with open(failure_log, "a", encoding="utf-8") as fl:
                fl.write(f"[{datetime.datetime.now().isoformat()}] draft_doctor exception on post {post_id}: {e}\n")

        # Atomic Registry Update (STA-03)
        update_registry_atomic(post_id, title, html_path.name)

        # Extract ORIGINAL_TOPIC from HTML comment for master-list removal
        original_topic = None
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content_for_topic = f.read()
            import re as _re
            m = _re.search(r"<!--\s*ORIGINAL_TOPIC:\s*(.*?)\s*-->", html_content_for_topic)
            if m:
                original_topic = m.group(1).strip()
        except Exception:
            pass

        # Remove from master list to prevent duplicates (use ORIGINAL_TOPIC if available)
        remove_site_from_master_list(original_topic or title)

        safe_atomic_move(html_path, PROCESSED_DIR)
        print(f"  [OK] SUCCESS: {html_path.name} moved to processed.")
    else:
        safe_atomic_move(html_path, FAILED_DIR)
        print(f"  [FAIL] FAILED: {html_path.name} moved to failed.")

def main():
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    FAILED_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Discover and convert any pending .docx posts to .html
    docx_files = list(PENDING_DIR.glob("*.docx"))
    if docx_files:
        print(f"Found {len(docx_files)} .docx file(s) in pending. Converting to HTML...")
        for docx_file in docx_files:
            convert_docx_to_html(docx_file)

    # 2. Collect all pending HTML posts
    pending_files = sorted(list(PENDING_DIR.glob("*.html")))
    if not pending_files:
        print("No pending posts found in content/pending.")
        return

    print(f"Found {len(pending_files)} HTML post(s) to process.")
    for i, html_file in enumerate(pending_files, 1):
        print(f"\n[{i}/{len(pending_files)}] Processing {html_file.name}...")
        process_post(html_file)
    
    # Auto-update topic lists after batch completes
    print("\n--- Updating Topic Tracker ---")
    try:
        run_topic_tracker()
    except Exception as e:
        print(f"[Tracker] Failed to update topic lists: {e}")

if __name__ == "__main__":
    main()
