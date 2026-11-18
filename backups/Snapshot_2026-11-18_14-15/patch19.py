for p in ['post_inspector.py','draft_doctor.py']:
    s=open(p,encoding='utf-8').read()
    if 'io.TextIOWrapper' not in s:
        s='import sys\nimport io\nif sys.stdout.encoding != "utf-8":\n    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")\n\n'+s
    open(p,'w',encoding='utf-8').write(s)
print('done')
