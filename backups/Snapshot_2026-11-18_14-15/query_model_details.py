import sqlite3

conn = sqlite3.connect(r'C:\Users\Nasir\AppData\Roaming\FreeLLMAPI\freeapi.db')
cursor = conn.cursor()
model_ids = [2, 3, 16, 20, 21, 23, 52, 53, 59, 60, 61, 62, 65, 66, 67, 68, 70, 75, 76, 80, 84, 100, 102, 112, 119, 120, 121, 122, 128, 129]
with open('model_details.txt', 'w', encoding='utf-8') as f:
    for mid in model_ids:
        cursor.execute(f'SELECT * FROM models WHERE id = {mid}')
        row = cursor.fetchone()
        if row:
            f.write(str(row) + '\n')