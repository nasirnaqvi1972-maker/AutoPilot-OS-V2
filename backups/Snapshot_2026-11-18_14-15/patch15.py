p='safe_batch.py'
s=open(p,encoding='utf-8').read()
old='''    success = publish_post(
        html_path=curated_html_path,
        img_folder=img_folder,
        title=title,
        labels=[]
    )
    
    if success:'''
new='''    post_id = publish_post(
        html_path=curated_html_path,
        img_folder=img_folder,
        title=title,
        labels=[]
    )
    
    if post_id:
        try:
            subprocess.run([str(Path(__file__).resolve().parent / "os_env" / "Scripts" / "python.exe"), str(Path(__file__).resolve().parent / "draft_doctor.py"), str(post_id)], cwd=str(Path(__file__).resolve().parent))
        except Exception as e:
            print(f"  [doctor] failed: {e}")
    
    if post_id:'''
assert old in s
s=s.replace(old,new)
# ensure subprocess imported
if 'import subprocess' not in s:
    s=s.replace('import shutil','import shutil\nimport subprocess')
open(p,'w',encoding='utf-8').write(s)
print('done')
