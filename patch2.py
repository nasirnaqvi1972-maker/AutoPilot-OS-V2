p='safe_batch.py'
s=open(p,encoding='utf-8').read()
s=s.replace('\u274c','[FAIL]').replace('\u2705','[OK]')
open(p,'w',encoding='utf-8').write(s)
print('done')
