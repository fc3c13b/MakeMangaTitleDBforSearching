"""
fetch_readings.py - AI APIで読み方（ふりがな）を取得してDBに保存

Step 3: APIフェッチ & DB格納
入力:  batch_groups.json, manga_titles.db
出力: manga_titles.db (更新済み)
"""
import json
import os
import time
import sqlite3
import sys
import argparse
from config import get_db_path
from google import genai

# APIレート制限マージンを含む待機時間（秒）
# DELAY=10秒 → RPM消費率40%（15回/分のうち6回/分）
DELAY = 10.0


def fetch_readings_batch(client, model, titles: list, group_id: int) -> dict:
    """AI APIを使用して複数のタイトルに対して読み方を取得"""
    titles_text = "\n".join(f"{i+1}. {t}" for i, t in enumerate(titles))
    
    prompt = f"""You are a Japanese reading assistant. For each manga title listed below, provide the hiragana reading (ふりがな).

RULES:
1. Return readings for ALL titles listed - do not skip any
2. Use ONLY hiragana (平仮名) for readings
3. If uncertain or ambiguous, use "unknown" as the reading
4. Return valid JSON only - no extra text

SPECIAL CONSIDERATIONS:
- Some titles may contain romanized text (e.g. "shinwa", "tatsujin"). Treat them as Japanese words and provide the standard Japanese reading.
- Some titles may include author names, volume numbers, language tags, or decorative symbols (like #, &, ~, etc.). Focus ONLY on the actual manga title and provide its Japanese reading.
- Even if the title appears in English, provide the reading as if it were the Japanese title used in Japan.

TITLES:
{titles_text}

OUTPUT FORMAT (flat structure - do NOT use nested arrays):
{{"group_id": {group_id}, "readings": {{"title1": "reading1", "title2": "reading2", ...}}}}"""
    
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config={"temperature": 0, "top_p": 1, "top_k": 1}
        )
        
        text = response.text.strip()
        # JSON文字列を抽出（マークダウンの```json ... ```を除去）
        if text.startswith('```'):
            lines = text.split('\n')
            json_start = next((i for i, line in enumerate(lines) if '```' in line), 0)
            json_end = next((i for i, line in enumerate(lines) if '```' in line and i > json_start), len(lines))
            text = '\n'.join(lines[json_start + 1:json_end])
        
        data = json.loads(text)
        return data
    
    except json.JSONDecodeError as e:
        print(f"  JSON解析エラー: {e}")
        print(f"  応答: {text[:200]}...")
        return {"group_id": group_id, "readings": {}}
    except Exception as e:
        print(f"  API呼び出しエラー: {e}")
        return {"group_id": group_id, "readings": {}}


def main():
    parser = argparse.ArgumentParser(description="AI APIで読み方を取得")
    parser.add_argument(
        "--start", type=int, default=0,
        help="開始グループID (default: 0)"
    )
    parser.add_argument(
        "--end", type=int, default=None,
        help="終了グループID (default: 最後)"
    )
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = get_db_path()
    groups_path = os.path.join(base_dir, "batch_groups.json")

    if not os.path.exists(groups_path):
        print(f"Error: {groups_path} not found. Run group_titles.py first.", file=sys.stderr)
        sys.exit(1)

    print(f"Loading {groups_path} ...")
    with open(groups_path, 'r', encoding='utf-8') as f:
        groups = json.load(f)
    
    start = args.start
    end = args.end if args.end is not None else len(groups)
    groups_to_process = groups[start:end]
    
    print(f"Processing groups {start} to {end - 1} ({len(groups_to_process)} groups).")
    
    # DBにreadingカラムが存在しない場合は追加
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(folder_titles)")
    columns = [col[1] for col in cursor.fetchall()]
    if "reading" not in columns:
        cursor.execute("ALTER TABLE folder_titles ADD COLUMN reading TEXT DEFAULT ''")
        conn.commit()
        print("reading カラムを追加しました")
    conn.close()

    # Gemini API クライアントの初期化
    print("Initializing Gemini client ...")
    client = genai.Client(vertexai=False, api_key=os.environ.get("GOOGLE_API_KEY", ""))
    model = "gemini-2.0-flash"
    
    success_count = 0
    fail_count = 0
    all_failed_titles = []

    for group in groups_to_process:
        group_id = group["group_id"]
        batch = group["titles"]
        
        print(f"\n--- Group {group_id} ({len(batch)}件, {sum(len(t) for t in batch)}文字) ---")
        
        result = fetch_readings_batch(client, model, batch, group_id)
        readings = result.get("readings", {})
        
        # DBに保存
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        for title in batch:
            if title in readings:
                cursor.execute(
                    "UPDATE folder_titles SET reading = ? WHERE folder_name = ? COLLATE NOCASE",
                    (readings[title], title)
                )
                if cursor.rowcount == 0:
                    # folder_titles に存在しない場合は新規追加
                    cursor.execute(
                        "INSERT INTO folder_titles (folder_name, correct_title, reading, confidence, source) "
                        "VALUES (?, ?, ?, 1.0, 'llm_reading')",
                        (title, title, readings[title])
                    )
                success_count += 1
            else:
                fail_count += 1
                all_failed_titles.append(title)
                safe_title = title.encode('cp932', errors='replace').decode('cp932')
                print(f"  読み方取得失敗: {safe_title}")
        
        conn.commit()
        conn.close()
        
        print(f"  成功: {success_count}件, 失敗: {fail_count}件")
        
        time.sleep(DELAY)
    
    # サマリー表示
    print(f"\n{'='*50}")
    print(f"=== 処理完了 ===")
    print(f"{'='*50}")
    print(f"成功: {success_count}件")
    print(f"失敗: {fail_count}件")
    print(f"合計: {success_count + fail_count}件")
    
    # 失敗詳細を表示
    if all_failed_titles:
        print(f"\n--- 失敗タイトル一覧 ({len(all_failed_titles)}件) ---")
        for title in sorted(all_failed_titles):
            safe_title = title.encode('cp932', errors='replace').decode('cp932')
            print(f"  - {safe_title}")
    
    # サマリーをファイルに保存
    summary_path = os.path.join(base_dir, "summary.json")
    summary_data = {
        "timestamp": time.time(),
        "success_count": success_count,
        "fail_count": fail_count,
        "total": success_count + fail_count,
        "failed_titles": all_failed_titles,
        "files": {
            "db": db_path,
        }
    }
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)
    print(f"サマリー:   {summary_path}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()