p='safe_batch.py'
s=open(p,encoding='utf-8').read()
old='''    try:
        success = curate_images(html_path, img_folder)
    except Exception as e:
        print(f"  [FAIL] Curator crashed: {e}")
        traceback.print_exc()
        success = False'''
new='''    soup_check = BeautifulSoup(html_content, "html.parser")
    existing_imgs = soup_check.find_all("img")
    if len(existing_imgs) >= 1:
        print(f"  [Engine] Post already contains {len(existing_imgs)} images. Skipping Auto-Image fetching.")
        success = True
        # ensure img_folder exists
        img_folder.mkdir(parents=True, exist_ok=True)
        # copy html to curated output
        curated_html_path = img_folder / "_output.html"
        curated_html_path.write_text(html_content, encoding="utf-8")
    else:
        print("  [Engine] No images found. Fetching 7 images from Unsplash...")
        try:
            success = curate_images(html_path, img_folder)
        except Exception as e:
            print(f"  [FAIL] Curator crashed: {e}")
            traceback.print_exc()
            success = False'''
assert old in s
s=s.replace(old,new)
open(p,'w',encoding='utf-8').write(s)
print('done')
