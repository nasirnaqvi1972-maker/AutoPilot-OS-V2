for p in ['post_inspector.py','draft_doctor.py']:
    s=open(p,encoding='utf-8').read()
    s=s.replace('🔴 CRITICAL:','[CRITICAL]').replace('🟡 WARNING:','[WARNING]').replace('🟢 PASS:','[PASS]')
    open(p,'w',encoding='utf-8').write(s)
print('done')
