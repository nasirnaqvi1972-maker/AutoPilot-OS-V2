p='core/image_curator.py'
s=open(p,encoding='utf-8').read()
# add vision_check function before download_image
anchor='def download_image(url, save_path):'
func='''def vision_check(image_path):
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

'''
assert anchor in s
s=s.replace(anchor, func+anchor, 1)
# insert vision check in download loop after md5/phash, before aesthetic
old='''            # vision anti-monkey check
            try:
                pos = contrastive_clip_score(temp_path, "stone architecture caves ruins statues", "stone architecture caves ruins statues", "")
                # reuse clip score against negative by direct encode
            except Exception:
                pass
            try:'''
new='''            if not vision_check(temp_path):
                os.remove(temp_path)
                continue
            try:'''
assert old in s
s=s.replace(old,new)
open(p,'w',encoding='utf-8').write(s)
print('done')
