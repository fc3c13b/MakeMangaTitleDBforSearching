"""
search_media_arts.py - Media Arts Database API 経由で漫画タイトルを検索

API エンドポイント:
  GET https://mediaarts-db.artmuseums.go.jp/es-api/?query=<json>

Elasticsearchクエリで title/name フィールドをマッチングし、
結果から schema.org/name の値を抽出。

使用例:
  python search_media_arts.py --titles naruto one-piece
  python search_media_arts.py --input titles.csv -o media_arts_results.csv
"""

import csv
import json
import os
import re
import time
import urllib3
from typing import List, Dict, Optional, Tuple

import requests

# SSL検証警告を抑制
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://mediaarts-db.artmuseums.go.jp/es-api/"
REQUEST_DELAY = 0.8   # 1.5回/秒のレート制限マージン (0.67秒以上必要)
BATCH_SIZE = 20        # 1回のクエリで返す最大ヒット数


def search_title(title: str, size: int = BATCH_SIZE) -> List[Dict]:
    """
    単一タイトルを Media Arts DB で検索
    
    Args:
        title: 検索する漫画タイトル
        size: 返す結果数
    
    Returns:
        検索結果リスト。各要素は {"title": str, "entity_id": str, "score": float}
    """
    max_retries = 5
    for attempt in range(max_retries):
        resp = requests.get(
            BASE_URL,
            params={"q": title, "size": size},
            timeout=30,
            verify=False,
        )
        if resp.status_code == 429:
            wait = 5 + (attempt + 1) * 5
            print(f"  [レート制限] {title} → {wait}秒待機後再試行...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        data = resp.json()
        break
    else:
        print(f"  [エラー] APIリクエスト失敗: {title} → {resp.status_code}")
        return []

    hits = data.get("hits", {}).get("hits", [])
    results = []
    for hit in hits:
        source = hit.get("_source", {})
        predicates = source.get("predicates", {})
        name_list = predicates.get("https://schema.org/name", [])
        if name_list:
            actual_title = name_list[0].get("value", "")
            results.append({
                "title": actual_title,
                "entity_id": source.get("entity_id", ""),
                "score": hit.get("_score", 0.0) or 0.0,
            })
        elif source.get("title"):
            # フォールバック: titleフィールド直接使用
            results.append({
                "title": source["title"],
                "entity_id": source.get("entity_id", ""),
                "score": hit.get("_score", 0.0) or 0.0,
            })
    return results


def batch_search(titles: List[str], delay: float = REQUEST_DELAY) -> Dict[str, List[Dict]]:
    """
    タイトルリストをバッチ処理で検索
    
    Args:
        titles: 検索したいタイトルリスト
        delay: リクエスト間の待機秒数
    
    Returns:
        {タイトル: [検索結果リスト]} の辞書
    """
    results: Dict[str, List[Dict]] = {}
    total = len(titles)
    
    for i, title in enumerate(titles):
        print(f"  [{i+1}/{total}] {title}")
        results[title] = search_title(title)
        time.sleep(delay)
    
    return results


def save_results(results: Dict[str, List[Dict]], output_path: str):
    """検索結果をCSVに保存"""
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["query_title", "matched_title", "entity_id", "score", "rank"])
        for query_title, hits in results.items():
            for rank, hit in enumerate(hits, 1):
                writer.writerow([
                    query_title,
                    hit["title"],
                    hit["entity_id"],
                    round(hit["score"], 4),
                    rank,
                ])
    print(f"\n結果を保存しました: {output_path}")


def load_titles_from_csv(csv_path: str) -> List[str]:
    """CSVからタイトルリストを読み込む"""
    titles = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        # correct_title または title カラムがあればそれを使う
        if "correct_title" in reader.fieldnames:
            col = "correct_title"
        elif "title" in reader.fieldnames:
            col = "title"
        else:
            col = reader.fieldnames[0]
        for row in reader:
            t = row.get(col, "").strip()
            if t and t not in titles:
                titles.append(t)
    return titles


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Media Arts Database で漫画タイトルを検索",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 単一タイトルを検索
  python search_media_arts.py --title "NARUTO"

  # 複数のタイトルを指定
  python search_media_arts.py --titles naruto one-piece bleach

  # CSVから読み込んで検索
  python search_media_arts.py --input results.csv -o media_arts_results.csv
        """,
    )
    parser.add_argument("--title", type=str, help="単一タイトルを検索")
    parser.add_argument("--titles", nargs="+", type=str, help="スペース区切りのタイトルリスト")
    parser.add_argument("--input", type=str, help="入力CSVファイルパス")
    parser.add_argument("--output", "-o", type=str, default="media_arts_results.csv", help="出力CSVパス")
    parser.add_argument("--size", type=int, default=BATCH_SIZE, help="1クエリあたりの結果数 (default: 20)")
    parser.add_argument("--delay", type=float, default=REQUEST_DELAY, help="リクエスト間隔秒 (default: 0.3)")

    args = parser.parse_args()

    # タイトル収集
    titles = []
    if args.title:
        titles = [args.title]
    elif args.titles:
        titles = args.titles
    elif args.input:
        if not os.path.exists(args.input):
            print(f"ファイルが見つかりません: {args.input}")
            return
        titles = load_titles_from_csv(args.input)
        print(f"CSVから {len(titles)}件のタイトルを読み込みました")
    else:
        parser.print_help()
        return

    print(f"\nMedia Arts DB 検索開始 ({len(titles)}件)")
    print("=" * 60)

    results = batch_search(titles, delay=args.delay)

    # 結果サマリー
    total_hits = sum(len(v) for v in results.values())
    with_hits = sum(1 for v in results.values() if v)
    print(f"\n--- 検索完了 ---")
    print(f"  検索済み: {len(results)}件")
    print(f"  ヒットあり: {with_hits}件")
    print(f"  総ヒット数: {total_hits}件")

    # 出力
    save_results(results, args.output)


if __name__ == "__main__":
    main()
