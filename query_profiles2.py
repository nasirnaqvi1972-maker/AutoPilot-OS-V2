import sqlite3

conn = sqlite3.connect(r'C:\Users\Nasir\AppData\Roaming\FreeLLMAPI\freeapi.db')
cursor = conn.cursor()
cursor.execute('SELECT * FROM profiles')
with open('profiles_out.txt', 'w', encoding='utf-8') as f:
    for row in cursor.fetchall():
        f.write(str(row) + '\n')

cursor.execute('SELECT * FROM profile_models LIMIT 30')
with open('profile_models_out.txt', 'w', encoding='utf-8') as f:
    for row in cursor.fetchall():
        f.write(str(row) + '\n')