p='core/image_curator.py'
s=open(p,encoding='utf-8').read()
# ensure hashlib import
if 'import hashlib' not in s:
    s=s.replace('import os, re, json, time, shutil, tempfile, urllib.parse, urllib.request, html','import os, re, json, time, shutil, tempfile, urllib.parse, urllib.request, html, hashlib')
# add md5 set init near hashes
s=s.replace('    img_count = 0\n    hashes = set()\n','    img_count = 0\n    hashes = set()\n    md5_hashes = set()\n')
# after successful download, before aesthetic filter, insert md5 check
old='''        if download_image(url, temp_path):
            if not passes_aesthetic_filter(temp_path):'''
new='''        if download_image(url, temp_path):
            with open(temp_path, "rb") as f:
                md5 = hashlib.md5(f.read()).hexdigest()
            if md5 in md5_hashes:
                print("      [Image Validator] Skipping duplicate image (MD5 match).")
                os.remove(temp_path)
                continue
            md5_hashes.add(md5)
            if not passes_aesthetic_filter(temp_path):'''
assert old in s
s=s.replace(old,new)
open(p,'w',encoding='utf-8').write(s)
print('done')
