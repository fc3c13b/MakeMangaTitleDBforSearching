"""
clean_titles.py - 生タイトルリストの簡略化・重複削除

入力:  dl_raw_titles.txt
出力:  cleaned_titles.json（一意の簡略化済みタイトル配列）
"""
import json
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH = os.path.join(BASE_DIR, "dl_raw_titles.txt")
OUTPUT_PATH = os.path.join(BASE_DIR, "cleaned_titles.json")

# 簡略化パターン（出現順に適用）
CLEAN_PATTERNS = [
    r'\s*\[.*?\]',          # [Romaji] 等（括弧閉じあり）
    r'\s*\[.*',             # 括弧閉じがない [ の場合
    r'\s*第\d{1,2}-\d{1,2}巻',  # 巻範囲（例: 第01-02巻）
    r'\s*全\d+巻',          # 総巻数（例: 全45巻）
    r'\s*第\d{1,2}巻',      # 単一巻番号（例: 第01巻）
    r'\s*raw\s+全\d+巻',    # raw 全XX巻
    r'\s*上下巻',            # 上下巻
    r'\s*全\d{1,2}巻',      # 全1巻等（短書式）
]


def clean_title(title: str) -> str:
    """タイトルから巻番号・Romaji等を削除"""
    for pat in CLEAN_PATTERNS:
        title = re.sub(pat, '', title)
    return title.strip()


def main():
    if not os.path.exists(INPUT_PATH):
        print(f"Error: {INPUT_PATH} not found.", file=sys.stderr)
        sys.exit(1)

    print(f"Loading {INPUT_PATH} ...")
    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        raw_lines = [l.strip() for l in f if l.strip()]

    print(f"  Loaded {len(raw_lines)} entries.")

    # 簡略化
    print("Cleaning titles ...")
    cleaned = []
    for line in raw_lines:
        c = clean_title(line)
        if c:
            cleaned.append(c)

    print(f"  After cleaning: {len(cleaned)} entries.")

    # 重複削除（出現順序保持）
    print("Deduplicating ...")
    seen = set()
    unique = []
    for c in cleaned:
        if c not in seen:
            seen.add(c)
            unique.append(c)

    print(f"  Unique: {len(unique)} entries "
          f"(removed {len(cleaned) - len(unique)} duplicates).")

    # JSON出力
    output = [{"id": i, "title": t} for i, t in enumerate(unique)]

    print(f"Saving to {OUTPUT_PATH} ...")
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"  Done. {len(output)} entries saved.")


if __name__ == '__main__':
    main()
