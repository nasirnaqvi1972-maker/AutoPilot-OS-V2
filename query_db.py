import sqlite3

conn = sqlite3.connect(r'C:\Users\Nasir\AppData\Roaming\FreeLLMAPI\freeapi.db')
cursor = conn.cursor()
cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = cursor.fetchall()
print('Tables:', tables)
for table in tables:
    t = table[0]
    print(f'\n--- {t} ---')
    cursor.execute(f'SELECT * FROM {t} LIMIT 10')
    for row in cursor.fetchall():
        print(row)