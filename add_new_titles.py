"""
add_new_titles.py - 新規タイトルの重複チェック・追加

入力:  dl_raw_titles.txt, cleaned_titles.json
出力: cleaned_titles.json (更新済み)
"""
import json
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_INPUT = os.path.join(BASE_DIR, "dl_raw_titles.txt")
CLEANED_PATH = os.path.join(BASE_DIR, "cleaned_titles.json")
BATCH_GROUPS_PATH = os.path.join(BASE_DIR, "batch_groups.json")

# clean_titles.py と同じ簡略化パターン
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
    if not os.path.exists(RAW_INPUT):
        print(f"Error: {RAW_INPUT} not found.", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(CLEANED_PATH):
        print(f"Error: {CLEANED_PATH} not found. Run clean_titles.py first.", file=sys.stderr)
        sys.exit(1)

    # 1. 既存のcleaned_titles.jsonを読み込む
    print(f"Loading {CLEANED_PATH} ...")
    with open(CLEANED_PATH, 'r', encoding='utf-8') as f:
        existing = json.load(f)

    existing_titles = set()
    for item in existing:
        existing_titles.add(item['title'])
    existing_max_id = max((item['id'] for item in existing), default=-1)
    print(f"  Existing: {len(existing_titles)} unique titles.")

    # 2. dl_raw_titles.txtを読み込んで簡略化
    print(f"Loading {RAW_INPUT} ...")
    with open(RAW_INPUT, 'r', encoding='utf-8') as f:
        raw_lines = [l.strip() for l in f if l.strip()]
    print(f"  Raw entries: {len(raw_lines)}")

    print("Cleaning new titles ...")
    cleaned = [clean_title(line) for line in raw_lines]
    cleaned = [c for c in cleaned if c]  # 空文字を除外

    # 3. 既存との重複排除（新規のみ抽出）
    print("Deduplicating against existing ...")
    new_unique = []
    seen = set(existing_titles)
    for c in cleaned:
        if c not in seen:
            seen.add(c)
            new_unique.append(c)

    if not new_unique:
        print("  No new titles found. Done.")
        return

    print(f"  New unique titles: {len(new_unique)}")

    # 4. cleaned_titles.json に追記
    new_entries = []
    for i, title in enumerate(new_unique):
        new_entries.append({"id": existing_max_id + i + 1, "title": title})

    updated = existing + new_entries

    print(f"Saving to {CLEANED_PATH} ...")
    with open(CLEANED_PATH, 'w', encoding='utf-8') as f:
        json.dump(updated, f, ensure_ascii=False, indent=2)
    print(f"  Done. Total {len(updated)} titles saved.")

    # 5. batch_groups.json の再構築（group_titles.py のロジックを再利用）
    print("Rebuilding batch_groups.json ...")
    from group_titles import split_titles_by_char_limit, MAX_INPUT_CHARS, TITLES_PER_BATCH_MAX

    all_titles = [item['title'] for item in updated]
    batches = split_titles_by_char_limit(all_titles, MAX_INPUT_CHARS, TITLES_PER_BATCH_MAX)

    groups = []
    for i, batch in enumerate(batches):
        groups.append({"group_id": i, "titles": batch})

    with open(BATCH_GROUPS_PATH, 'w', encoding='utf-8') as f:
        json.dump(groups, f, ensure_ascii=False, indent=2)
    print(f"  Done. {len(groups)} groups saved.")


if __name__ == '__main__':
    main()