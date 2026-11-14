import sqlite3

conn = sqlite3.connect(r'C:\Users\Nasir\AppData\Roaming\FreeLLMAPI\freeapi.db')
cursor = conn.cursor()
cursor.execute('SELECT * FROM profiles')
for row in cursor.fetchall():
    print(row)

print("\n--- profile_models ---")
cursor.execute('SELECT * FROM profile_models LIMIT 30')
for row in cursor.fetchall():
    print(row)