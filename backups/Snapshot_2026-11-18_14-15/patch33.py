p='safe_batch.py'
s=open(p,encoding='utf-8').read()
# import location detector
if 'from location_detector import detect_location' not in s:
    s=s.replace('from core.image_curator import curate_images','from core.image_curator import curate_images\nfrom location_detector import detect_location')
# before publish, compute labels
old='''    post_id = publish_post(
        html_path=curated_html_path,
        img_folder=img_folder,
        title=title,
        labels=[],
        post_id=existing_id
    )'''
new='''    labels = detect_location(title, html_content)
    print(f"  [Engine] Assigned labels: {', '.join(labels) if labels else 'none'}.")

    post_id = publish_post(
        html_path=curated_html_path,
        img_folder=img_folder,
        title=title,
        labels=labels,
        post_id=existing_id
    )'''
assert old in s
s=s.replace(old,new)
open(p,'w',encoding='utf-8').write(s)
print('done')
