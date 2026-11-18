p='safe_batch.py'
s=open(p,encoding='utf-8').read()
if 'import traceback' not in s:
    s=s.replace('import shutil','import shutil\nimport traceback')
s=s.replace('        print(f"  [FAIL] Curator crashed: {e}")','        print(f"  [FAIL] Curator crashed: {e}")\n        traceback.print_exc()')
open(p,'w',encoding='utf-8').write(s)
print('done')
