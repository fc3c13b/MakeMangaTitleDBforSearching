"""
match_titles.py - 抽出タイトルと Media Arts DB 検索結果の fuzzy matching

Media Arts DB 検索結果 (media_arts_results.csv) と DB 内のタイトルを
類似度でマッチングし、正解タイトルとして確定する。

マッチングアルゴリズム:
  1. 完全一致 → 確定
  2. 正規化後一致 (半角→全角, 記号除去等)
  3. SequenceMatcher の ratio > threshold → 候補提示
  4. 手動確認が必要なものを pending に分離

使用例:
  python match_titles.py
  python match_titles.py --input media_arts_results.csv --db manga_titles.db
"""

import csv
import os
import re
import sqlite3
import unicodedata
from typing import List, Dict, Tuple, Optional

from config import get_db_path
from database import get_connection, initialize_database, insert_folder_title

MATCH_THRESHOLD = 0.85  # 自動マッチングの類似度閾値


def normalize(s: str) -> str:
    """文字列を正規化 (fuzzy matching 用)"""
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r'[\s\p{P}\p{S}]', '', s)
    return s.lower()


def similarity(a: str, b: str) -> float:
    """2文字列の類似度を 0.0〜1.0 で返す"""
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio()


def find_best_match(query_title: str, candidates: List[Dict]) -> Optional[Dict]:
    """候補リストから最良のマッチを探す"""
    if not candidates:
        return None
    
    norm_query = normalize(query_title)
    
    # 完全一致チェック
    for c in candidates:
        if normalize(c["title"]) == norm_query:
            return c
    
    # 類似度でソート
    scored = []
    for c in candidates:
        sim = similarity(norm_query, normalize(c["title"]))
        scored.append((sim, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    
    if scored:
        best_sim, best_hit = scored[0]
        if best_sim >= MATCH_THRESHOLD:
            return best_hit
    
    return None


def load_media_arts_results(csv_path: str) -> Dict[str, List[Dict]]:
    """Media Arts DB の検索結果CSVを読み込む"""
    results: Dict[str, List[Dict]] = {}
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            qt = row["query_title"]
            hit = {
                "title": row["matched_title"],
                "entity_id": row["entity_id"],
                "score": float(row["score"]) if row["score"] else 0.0,
            }
            if qt not in results:
                results[qt] = []
            results[qt].append(hit)
    return results


def run_matching(
    media_arts_csv: str,
    db_path: Optional[str] = None,
    threshold: float = MATCH_THRESHOLD,
) -> Tuple[List[Dict], List[Dict]]:
    """Matching を実行し、(matched, pending) の2つのリストを返す"""
    if db_path is None:
        db_path = get_db_path()
    
    results = load_media_arts_results(media_arts_csv)
    matched: List[Dict] = []
    pending: List[Dict] = []
    total = len(results)
    
    for i, (query_title, candidates) in enumerate(results.items()):
        best = find_best_match(query_title, candidates)
        
        if best:
            matched.append({
                "folder_name": query_title,
                "correct_title": best["title"],
                "confidence": 0.95,
                "source": "media_arts_db",
                "entity_id": best["entity_id"],
                "method": "auto_matched",
            })
            insert_folder_title(
                folder_name=query_title,
                correct_title=best["title"],
                confidence=0.95,
                source="media_arts_db",
                db_path=db_path,
            )
        else:
            pending.append({
                "folder_name": query_title,
                "candidates": candidates,
                "method": "needs_review",
            })
        
        if (i + 1) % 50 == 0 or (i + 1) == total:
            print(f"  処理中... {i+1}/{total}件 (マッチ済み: {len(matched)}, 未確定: {len(pending)})")
    
    return matched, pending


def export_pending(pending: List[Dict], output_path: str):
    """手動確認が必要な件をCSVにエクスポート"""
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["folder_name", "candidates"])
        for entry in pending:
            cands = "; ".join(
                f"{h['title']}(score:{h['score']:.2f})" for h in entry["candidates"]
            )
            writer.writerow([entry["folder_name"], cands])
    print(f"未確定件をエクスポート: {output_path} ({len(pending)}件)")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Media Arts DB 検索結果の fuzzy matching",
    )
    parser.add_argument(
        "--input", "-i", type=str, default="media_arts_results.csv",
        help="Media Arts DB 検索結果CSV (default: media_arts_results.csv)",
    )
    parser.add_argument("--db", type=str, default=None, help="データベースパス")
    parser.add_argument(
        "--threshold", type=float, default=MATCH_THRESHOLD,
        help="自動マッチング類似度閾値 (default: 0.85)",
    )
    parser.add_argument(
        "--output-pending", type=str, default="match_pending.csv",
        help="未確定件出力CSVパス",
    )

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ファイルが見つかりません: {args.input}")
        print("まず python search_media_arts.py --input <titles.csv> で検索を実行してください。")
        return

    initialize_database()
    print(f"\nMatching開始 ({args.input})")
    print(f"閾値: {args.threshold}")
    print("=" * 60)

    matched, pending = run_matching(
        media_arts_csv=args.input,
        db_path=args.db,
        threshold=args.threshold,
    )

    print(f"\n{'='*60}")
    print("=== Matching完了 ===")
    print(f"{'='*60}")
    print(f"  自動マッチ確定: {len(matched)}件")
    print(f"  手動確認必要:  {len(pending)}件")
    print(f"  合計:          {len(matched) + len(pending)}件")

    if pending:
        export_pending(pending, args.output_pending)


if __name__ == "__main__":
    main()

