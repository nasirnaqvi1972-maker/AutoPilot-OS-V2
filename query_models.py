import sqlite3

conn = sqlite3.connect(r'C:\Users\Nasir\AppData\Roaming\FreeLLMAPI\freeapi.db')
cursor = conn.cursor()
cursor.execute('SELECT * FROM models LIMIT 20')
for row in cursor.fetchall():
    print(row)