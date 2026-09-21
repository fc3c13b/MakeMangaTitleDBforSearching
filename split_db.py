import sqlite3

src = sqlite3.connect('manga_titles.db')
sc = src.cursor()

# テーブル定義を取得
sc.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='folder_titles'")
create_sql = sc.fetchone()[0]

sc.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='extraction_rules'")
rules_sql = sc.fetchone()

sc.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='processing_log'")
log_sql = sc.fetchone()

# データを取得
sc.execute("SELECT * FROM folder_titles WHERE folder_name GLOB '[0-9]*'")
a_rows = sc.fetchall()

sc.execute("SELECT * FROM folder_titles WHERE folder_name NOT GLOB '[0-9]*'")
b_rows = sc.fetchall()

src.close()

# A: 数字/#で始まるタイトル
a_db = sqlite3.connect('manga_titles_numbers.db')
a_c = a_db.cursor()
a_c.execute(create_sql)
if rules_sql:
    a_c.execute(rules_sql[0])
if log_sql:
    a_c.execute(log_sql[0])
a_c.executemany("INSERT INTO folder_titles VALUES (?, ?, ?, ?, ?, ?, ?, ?)", a_rows)
a_db.commit()
a_db.close()

# B: それ以外
b_db = sqlite3.connect('manga_titles_others.db')
b_c = b_db.cursor()
b_c.execute(create_sql)
if rules_sql:
    b_c.execute(rules_sql[0])
if log_sql:
    b_c.execute(log_sql[0])
b_c.executemany("INSERT INTO folder_titles VALUES (?, ?, ?, ?, ?, ?, ?, ?)", b_rows)
b_db.commit()
b_db.close()

print(f"A(数字): {len(a_rows)}件")
print(f"B(それ以外): {len(b_rows)}件")
