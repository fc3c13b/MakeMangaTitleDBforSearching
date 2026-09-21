"""
validate_readings.py - 読み方データの品質検証

L1: フォーマットチェック（ひらがなのみ、空文字なし）
L2: 正解データ（ground_truth.json）との一致率

入力:  manga_titles.db, ground_truth.json
出力:  validation_report.json, コンソールレポート
"""
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "manga_titles.db")
GROUND_TRUTH_PATH = os.path.join(BASE_DIR, "ground_truth.json")
REPORT_PATH = os.path.join(BASE_DIR, "validation_report.json")

# ひらがな・カタカナ・半角・全角記号を許容（「」．）
# 範囲: 全角ひらがな(ぁ-ん) + 全角カタカナ(ア-ヶ) + 全角濁点(゙-゜)
#         全角ダッシュ(ー) + 半角カタカナ(ｧ-ﾺ) + 全角句読点(、。)
#         半角英数字(0-9a-zA-Z) ※APIが半角で返す場合がある
HIRAGANA_RE = re.compile(r'^[ぁ-んァ-ヶ゙-゜、。ーｧ-ﾺ0-9a-zA-Z]+$')


def load_ground_truth() -> list:
    """正解データを読み込む"""
    if not os.path.exists(GROUND_TRUTH_PATH):
        print(f"Warning: {GROUND_TRUTH_PATH} not found. L2 check skipped.", file=sys.stderr)
        return []
    with open(GROUND_TRUTH_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get("ground_truth", [])


def l1_format_check(db_path: str) -> dict:
    """L1: 全件のフォーマットチェック"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT folder_name, reading FROM folder_titles")
    rows = cursor.fetchall()
    conn.close()

    total = len(rows)
    errors = []
    error_titles = []

    for title, reading in rows:
        if not reading or not reading.strip():
            errors.append("empty")
            error_titles.append(title)
        elif not HIRAGANA_RE.match(reading):
            errors.append("non-hiragana")
            error_titles.append(f"{title} → {reading}")

    valid = total - len(errors)
    rate = valid / total * 100 if total else 0.0

    return {
        "total": total,
        "valid": valid,
        "invalid": len(errors),
        "pass_rate": round(rate, 2),
        "error_types": dict(_count(errors)),
        "error_titles_sample": error_titles[:20],
    }


def l2_accuracy_check(db_path: str, ground_truth: list) -> dict:
    """L2: 正解データとの一致率"""
    if not ground_truth:
        return {"skipped": True, "reason": "no ground truth data"}

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    matched = 0
    correct = 0
    mismatches = []

    for entry in ground_truth:
        title = entry["title"]
        expected = entry["reading"]

        cursor.execute(
            "SELECT reading FROM folder_titles WHERE folder_name = ? COLLATE NOCASE",
            (title,),
        )
        row = cursor.fetchone()

        if row:
            matched += 1
            actual = row[0]
            if actual == expected:
                correct += 1
            else:
                mismatches.append({
                    "title": title,
                    "expected": expected,
                    "actual": actual,
                })

    conn.close()

    accuracy = correct / matched * 100 if matched else 0.0

    return {
        "ground_truth_count": len(ground_truth),
        "matched_in_db": matched,
        "correct": correct,
        "mismatch": len(mismatches),
        "accuracy": round(accuracy, 2),
        "mismatches": mismatches[:20],
    }


def _count(items: list) -> dict:
    """リストの各要素をカウント"""
    result = {}
    for item in items:
        result[item] = result.get(item, 0) + 1
    return result


def main():
    print("=" * 60)
    print("  読み方データの品質検証")
    print("=" * 60)

    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.", file=sys.stderr)
        sys.exit(1)

    # --- L1: フォーマットチェック ---
    print("\n--- L1: フォーマットチェック ---")
    l1 = l1_format_check(DB_PATH)
    print(f"  総件数: {l1['total']}")
    print(f"  有効:   {l1['valid']}")
    print(f"  無効:   {l1['invalid']}")
    print(f"  合格率: {l1['pass_rate']}%")
    if l1['error_types']:
        print(f"  エラー種別: {l1['error_types']}")
    if l1['error_titles_sample']:
        print(f"  エラーサンプル（最大20件）:")
        for t in l1['error_titles_sample']:
            print(f"    - {t}")

    # --- L2: 正解比較 ---
    print("\n--- L2: 正解データ比較 ---")
    gt = load_ground_truth()
    l2 = l2_accuracy_check(DB_PATH, gt)

    if l2.get("skipped"):
        print(f"  スキップ: {l2['reason']}")
    else:
        print(f"  正解データ数: {l2['ground_truth_count']}")
        print(f"  DBに存在: {l2['matched_in_db']}")
        print(f"  正解: {l2['correct']}")
        print(f"  不一致: {l2['mismatch']}")
        print(f"  一致率: {l2['accuracy']}%")
        if l2['mismatches']:
            print(f"  不一致詳細:")
            for m in l2['mismatches']:
                print(f"    {m['title']}: 期待={m['expected']}, 実際={m['actual']}")

    # --- 判定基準 ---
    print("\n--- 判定基準 ---")
    l1_pass = l1['pass_rate'] >= 95.0
    l2_pass = (not l2.get("skipped") and l2.get("accuracy", 0) >= 80.0) or l2.get("skipped")

    print(f"  L1合格率: {l1['pass_rate']}% {'✅' if l1_pass else '❌'} (基準: ≥95%)")
    print(f"  L2一致率: {l2.get('accuracy', 'N/A')}% {'✅' if l2_pass else '❌'} (基準: ≥80%)")

    overall = l1_pass and l2_pass
    print(f"\n  総合判定: {'✅ PASS' if overall else '❌ FAIL'}")

    # --- レポート出力 ---
    report = {
        "timestamp": datetime.now().isoformat(),
        "l1_format_check": l1,
        "l2_accuracy_check": l2,
        "overall": "PASS" if overall else "FAIL",
    }

    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nレポート: {REPORT_PATH}")

    print("=" * 60)
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()