p='safe_batch.py'
s=open(p,encoding='utf-8').read()
old='''    if post_id:
        try:
            subprocess.run([str(Path(__file__).resolve().parent / "os_env" / "Scripts" / "python.exe"), str(Path(__file__).resolve().parent / "draft_doctor.py"), str(post_id)], cwd=str(Path(__file__).resolve().parent))
        except Exception as e:
            print(f"  [doctor] failed: {e}")
    
    if post_id:'''
new='''    if post_id:
        print(f"[AutoPilot] Post published (ID: {post_id}). Automatically running Smart Image Replacer to fix context...")
        try:
            subprocess.run([str(Path(__file__).resolve().parent / "os_env" / "Scripts" / "python.exe"), str(Path(__file__).resolve().parent / "smart_image_replacer.py"), str(post_id)], cwd=str(Path(__file__).resolve().parent))
        except Exception as e:
            print(f"  [smart] failed: {e}")
        try:
            subprocess.run([str(Path(__file__).resolve().parent / "os_env" / "Scripts" / "python.exe"), str(Path(__file__).resolve().parent / "draft_doctor.py"), str(post_id)], cwd=str(Path(__file__).resolve().parent))
        except Exception as e:
            print(f"  [doctor] failed: {e}")
    
    if post_id:'''
assert old in s
s=s.replace(old,new)
open(p,'w',encoding='utf-8').write(s)
print('done')
