"""
fetch_readings.py - AI APIで読み方（ふりがな）を取得してDBに保存

Step 3: APIフェッチ & DB格納
入力:  batch_groups.json, manga_titles.db
出力: manga_titles.db (更新済み)
"""
import json
import logging
import os
import re
import time
import sqlite3
import sys
import argparse
from config import get_db_path
from checkpoint import save_checkpoint, load_checkpoint, delete_checkpoint
from google import genai

# logging設定（ERRORのみ永続保存、INFOは一時的）
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
# ERRORハンドラー：1MBでローテート、最大3ファイル保持
import logging.handlers
error_handler = logging.handlers.RotatingFileHandler(
    'fetch_readings_errors.log',
    maxBytes=1 * 1024 * 1024,  # 1 MB
    backupCount=3,
    encoding='utf-8'
)
error_handler.setLevel(logging.ERROR)
logging.getLogger().addHandler(error_handler)

# APIレート制限マージンを含む待機時間（秒）
# DELAY=10秒 → RPM消費率40%（15回/分のうち6回/分）
DELAY = 10.0


def fetch_readings_batch(client, model, titles: list, group_id: int, max_batch_size: int = 40) -> dict:
    """AI APIを使用して複数のタイトルに対して読み方を取得"""
    # バッチを小さなサブバッチに分割（PROHIBITED_CONTENT回避）
    results = {}
    for i in range(0, len(titles), max_batch_size):
        subset = titles[i:i + max_batch_size]
        titles_text = "\n".join(f"{i+1}. {t}" for i, t in enumerate(subset))
        
        prompt = f"""The following is a list of publicly released manga/series titles. These are well-known published works and do not contain any sensitive, adult, or restricted content. They are provided purely for data organization and classification purposes.

You are a Japanese reading assistant. For each manga title listed below, provide the hiragana reading (ふりがな).

RULES:
1. Return readings for ALL titles listed - do not skip any
2. Use ONLY hiragana (平仮名) for readings
3. If uncertain or ambiguous, use "unknown" as the reading
4. Return valid JSON only - no extra text

SPECIAL CONSIDERATIONS:
- Some titles may contain romanized text. Treat them as Japanese words.
- Some titles may include author names, volume numbers, language tags, or decorative symbols. Focus ONLY on the actual manga title.
- Even if the title appears in English, provide the reading as if it were the Japanese title.

TITLES:
{titles_text}

OUTPUT FORMAT:
{{"group_id": {group_id}, "readings": {{"title1": "reading1", "title2": "reading2", ...}}}}"""
        
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config={"temperature": 0, "top_p": 1, "top_k": 1}
            )
            
            text = getattr(response, 'text', None)
            if text is None:
                print(f"  response.text is None. finish_reason: {response.candidates[0].finish_reason if response.candidates else 'unknown'}")
                time.sleep(DELAY)
                continue
            text = text.strip()
            # JSON文字列を抽出（マークダウンの```json ... ```を除去）
            if text.startswith('```'):
                lines = text.split('\n')
                json_start = next((i for i, line in enumerate(lines) if '```' in line), 0)
                json_end = next((i for i, line in enumerate(lines) if '```' in line and i > json_start), len(lines))
                text = '\n'.join(lines[json_start + 1:json_end])
            
            data = json.loads(text)
            results.update(data.get("readings", {}))
        except json.JSONDecodeError as e:
            msg = f"JSON解析エラー: {e}"
            print(f"  {msg}")
            print(f"  応答: {text[:200]}...")
            logging.error(msg)
        except Exception as e:
            msg = f"API呼び出しエラー: {e}"
            print(f"  {msg}")
            print(f"  response: {response}")
            logging.error(msg)
        time.sleep(DELAY)
    
    return {"group_id": group_id, "readings": results}


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
    
    # チェックポイント読み込み（存在する場合）
    checkpoint_path = os.path.join(base_dir, "checkpoint.json")
    cp = load_checkpoint(checkpoint_path)
    start = args.start
    if cp:
        saved_group = cp.get("last_group_id", -1)
        start = max(start, saved_group + 1)
        print(f"チェックポイントから再開: グループ {saved_group + 1} から")
    
    db_path = get_db_path()
    groups_path = os.path.join(base_dir, "batch_groups.json")

    if not os.path.exists(groups_path):
        print(f"Error: {groups_path} not found. Run group_titles.py first.", file=sys.stderr)
        sys.exit(1)

    print(f"Loading {groups_path} ...")
    with open(groups_path, 'r', encoding='utf-8') as f:
        groups = json.load(f)
    
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
    config_path = os.path.join(base_dir, "config.json")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    api_key = os.environ.get("GOOGLE_API_KEY") or config.get("gemini_api_key", "")
    print(f"API key: {api_key[:10]}... (length: {len(api_key)})")
    client = genai.Client(vertexai=False, api_key=api_key)
    model = "gemini-3.5-flash-lite"
    
    success_count = 0
    fail_count = 0
    all_failed_titles = []
    all_ng_titles = []  # 漢字・アルファベット混入でNGになったタイトル（追加評価候補）

    for group in groups_to_process:
        group_id = group["group_id"]
        batch = group["titles"]
        
        print(f"\n--- Group {group_id} ({len(batch)}件, {sum(len(t) for t in batch)}文字) ---")
        
        result = fetch_readings_batch(client, model, batch, group_id)
        readings = result.get("readings", {})
        
        # DBに保存
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # ── 補正関数 ──────────────────────────────────────
        # 漢字（CJK統合漢字）とアルファベットを検出
        HIRAGANA_KATAKANA_RE = re.compile(r'^[ぁ-んァ-ヶー゙゜、。ｧ-ﾺ0-9\s]+$')

        def normalize_reading(raw: str) -> str:
            """スペース削除 + 半角ハイフンを全角に"""
            r = raw.strip().replace(' ', '')
            r = r.replace('-', 'ー')
            return r

        def is_pure_hiragana(text: str) -> bool:
            """ひらがな・カタカナ・記号のみで構成されているか"""
            return bool(HIRAGANA_KATAKANA_RE.match(text))
        # ──────────────────────────────────────────────────

        # NGタイトルを蓄積するリスト（追加タイトル候補用）
        group_failed_titles = []

        for title in batch:
            if title in readings:
                raw_reading = readings[title]
                reading = normalize_reading(raw_reading)

                if not is_pure_hiragana(reading):
                    # 漢字・アルファベット混入 → NG（不採用）
                    fail_count += 1
                    all_failed_titles.append(title)
                    group_failed_titles.append(title)
                    safe_title = title.encode('cp932', errors='replace').decode('cp932')
                    print(f"  読み方NG（混入）: {safe_title} → {reading}")
                    continue

                cursor.execute(
                    "UPDATE folder_titles SET reading = ? WHERE folder_name = ? COLLATE NOCASE",
                    (reading, title)
                )
                if cursor.rowcount == 0:
                    cursor.execute(
                        "INSERT INTO folder_titles (folder_name, correct_title, reading, confidence, source) "
                        "VALUES (?, ?, ?, 1.0, 'llm_reading')",
                        (title, title, reading)
                    )
                success_count += 1
            else:
                fail_count += 1
                all_failed_titles.append(title)
                safe_title = title.encode('cp932', errors='replace').decode('cp932')
                print(f"  読み方取得失敗: {safe_title}")
        
        conn.commit()
        conn.close()
        
        # チェックポイント保存
        save_checkpoint(checkpoint_path, group_id)
        
        print(f"  成功: {success_count}件, 失敗: {fail_count}件")
        
        # NGタイトルをグローバルリストに追加
        all_ng_titles.extend(group_failed_titles)
        
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
    
    # 漢字・アルファベット混入でNGになったタイトルをファイルに保存
    ng_path = os.path.join(base_dir, "ng_title_candidates.txt")
    with open(ng_path, 'w', encoding='utf-8') as f:
        for t in sorted(all_ng_titles):
            f.write(t + '\n')
    print(f"NGタイトル候補: {ng_path} ({len(all_ng_titles)}件)")
    
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
    
    # 全件処理完了 → チェックポイント削除
    delete_checkpoint(checkpoint_path)


if __name__ == "__main__":
    main()