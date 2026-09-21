import sqlite3

db = sqlite3.connect('manga_titles.db')
c = db.cursor()

# GLOB テスト
c.execute('SELECT folder_name FROM folder_titles WHERE folder_name GLOB "[0-9]*" LIMIT 5')
print("GLOB [0-9]*:", c.fetchall())

c.execute('SELECT folder_name FROM folder_titles WHERE folder_name GLOB "#*" LIMIT 5')
print("GLOB #*:", c.fetchall())

c.execute('SELECT folder_name FROM folder_titles LIMIT 10')
print("先頭10件:", [row[0] for row in c.fetchall()])

db.close()
