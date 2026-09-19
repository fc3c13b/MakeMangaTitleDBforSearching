"""
export_results.py - API処理結果の成功/失敗ファイルを生成

入力: manga_titles.db
出力: readings_success.csv, failed_titles.txt
"""
import csv
import sqlite3
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "manga_titles.db")
CSV_PATH = os.path.join(BASE_DIR, "readings_success.csv")
FAILED_PATH = os.path.join(BASE_DIR, "failed_titles.txt")


def main():
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.", file=sys.stderr)
        sys.exit(1)

    print(f"Loading {DB_PATH} ...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 成功したタイトルを取得（readingが空でないもの）
    cursor.execute(
        "SELECT folder_name, reading, source, confidence "
        "FROM folder_titles WHERE reading != '' AND reading IS NOT NULL"
    )
    successes = cursor.fetchall()
    print(f"  Found {len(successes)} successful readings.")

    # 失敗したタイトルを取得（readingが空またはNULLのもの）
    cursor.execute(
        "SELECT folder_name FROM folder_titles WHERE reading = '' OR reading IS NULL"
    )
    failures = cursor.fetchall()
    print(f"  Found {len(failures)} failed titles.")

    conn.close()

    # 成功CSVに書き込み
    print(f"Saving to {CSV_PATH} ...")
    with open(CSV_PATH, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['title', 'reading', 'source', 'confidence'])
        for row in successes:
            writer.writerow(row)
    print(f"  Done. {len(successes)} entries saved.")

    # 失敗TXTに書き込み
    print(f"Saving to {FAILED_PATH} ...")
    with open(FAILED_PATH, 'w', newline='', encoding='utf-8-sig') as f:
        for row in failures:
            f.write(f"{row[0]}\n")
    print(f"  Done. {len(failures)} entries saved.")


if __name__ == '__main__':
    main()