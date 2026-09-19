"""
group_titles.py - cleaned_titles.json を APIバッチング用にグルーピング

入力: cleaned_titles.json
出力: batch_groups.json
"""
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH = os.path.join(BASE_DIR, "cleaned_titles.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "batch_groups.json")

# APIレート制限マージンを含む待機時間（秒）
# DELAY=10秒 → RPM消費率40%（15回/分のうち6回/分）
DELAY = 10.0
# 入力文字数の制限（出力トークン80%制限を満たすよう計算）
# 推定: 80%×8192=6554トークン → 180タイトル/バッチ × 平均20字 = 3600字
MAX_INPUT_CHARS = 3600
TITLES_PER_BATCH_MAX = 180


def split_titles_by_char_limit(titles: list, max_chars: int, max_count: int) -> list:
    """文字数管理でバッチを分割"""
    batches = []
    current_batch = []
    current_chars = 0

    for title in titles:
        # 2つの条件で制限：
        # 1. タイトル数の上限（出力トークン制御）
        # 2. 文字数上限（入力トークン制御）
        if len(current_batch) >= max_count or current_chars + len(title) > max_chars:
            if current_batch:
                batches.append(current_batch)
            current_batch = []
            current_chars = 0

        current_batch.append(title)
        current_chars += len(title)

    if current_batch:
        batches.append(current_batch)

    return batches


def main():
    if not os.path.exists(INPUT_PATH):
        print(f"Error: {INPUT_PATH} not found.", file=sys.stderr)
        sys.exit(1)

    print(f"Loading {INPUT_PATH} ...")
    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        cleaned = json.load(f)

    titles = [item['title'] for item in cleaned]
    print(f"  Loaded {len(titles)} titles.")

    print("Grouping titles for API batching ...")
    batches = split_titles_by_char_limit(titles, MAX_INPUT_CHARS, TITLES_PER_BATCH_MAX)

    # batch_groups.json 形式: [{"group_id": 0, "titles": [...]}, ...]
    groups = []
    for i, batch in enumerate(batches):
        groups.append({"group_id": i, "titles": batch})

    print(f"  Created {len(groups)} groups.")

    print(f"Saving to {OUTPUT_PATH} ...")
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(groups, f, ensure_ascii=False, indent=2)

    print(f"  Done. {len(groups)} groups saved.")


if __name__ == '__main__':
    main()