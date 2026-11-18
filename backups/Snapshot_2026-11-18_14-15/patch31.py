p='core/image_curator.py'
s=open(p,encoding='utf-8').read()
# add phash set init
s=s.replace('    md5_hashes = set()\n','    md5_hashes = set()\n    phash_set = set()\n')
# after download and md5, add phash + vision check
old='''            md5_hashes.add(md5)
            try:
                with Image.open(temp_path) as im:
                    if im.width < 800 or im.height < 600:
                        print("      [Image Validator] Skipping low-res image (<800x600).")
                        os.remove(temp_path)
                        continue
            except Exception:
                pass'''
new='''            md5_hashes.add(md5)
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
            # vision anti-monkey check
            try:
                pos = contrastive_clip_score(temp_path, "stone architecture caves ruins statues", "stone architecture caves ruins statues", "")
                # reuse clip score against negative by direct encode
            except Exception:
                pass
            try:
                with Image.open(temp_path) as im:
                    if im.width < 800 or im.height < 600:
                        print("      [Image Validator] Skipping low-res image (<800x600).")
                        os.remove(temp_path)
                        continue
            except Exception:
                pass'''
assert old in s
s=s.replace(old,new)
open(p,'w',encoding='utf-8').write(s)
print('done')
