p='core/image_curator.py'
s=open(p,encoding='utf-8').read()
old='''            md5_hashes.add(md5)
            if not passes_aesthetic_filter(temp_path):'''
new='''            md5_hashes.add(md5)
            try:
                with Image.open(temp_path) as im:
                    if im.width < 800 or im.height < 600:
                        print("      [Image Validator] Skipping low-res image (<800x600).")
                        os.remove(temp_path)
                        continue
            except Exception:
                pass
            if not passes_aesthetic_filter(temp_path):'''
assert old in s
s=s.replace(old,new)
open(p,'w',encoding='utf-8').write(s)
print('done')
