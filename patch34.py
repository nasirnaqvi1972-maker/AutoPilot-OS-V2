p='draft_doctor.py'
s=open(p,encoding='utf-8').read()
if 'from location_detector import detect_location' not in s:
    s=s.replace('from bs4 import BeautifulSoup','from bs4 import BeautifulSoup\nsys.path.insert(0, r"D:\\Projects\\AutoPilot_OS_v2")\nfrom location_detector import detect_location')
# in fix_post, before patch, compute labels
old='''    if changed:
        body = {'id': post_id, 'title': post.get('title'), 'content': str(soup), 'searchDescription': meta}'''
new='''    labels = list(post.get('labels', []) or [])
    detected = detect_location(post.get('title',''), str(soup))
    for lab in detected:
        if lab not in labels:
            labels.append(lab)
    if changed or detected:
        body = {'id': post_id, 'title': post.get('title'), 'content': str(soup), 'searchDescription': meta, 'labels': labels}'''
assert old in s
s=s.replace(old,new)
# ensure body patch includes labels; remove duplicate labels line
s=s.replace("        if post.get('labels'):\n            body['labels'] = post['labels']\n","")
open(p,'w',encoding='utf-8').write(s)
print('done')
