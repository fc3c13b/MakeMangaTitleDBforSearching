"""
テスト：タイトル簡略化がAPI成功率に与える影響を評価する
"""
import re
import json
import time
from google import genai

# 失敗タイトルを取得
with open("summary.json", "r", encoding="utf-8") as f:
    data = json.load(f)

failed_titles = data.get("failed_titles", [])
print(f"テスト対象: {len(failed_titles)}件の失敗タイトル")
print()


def simplify_title(title: str) -> str:
    """巻数表記と[ローマ字]を削除"""
    # [xxx] のローマ字を削除
    title = re.sub(r'\s*\[.*?\]', '', title)
    # 第01-03巻 のような巻数表記を削除
    title = re.sub(r'第\d{1,2}-\d{1,2}巻', '', title)
    # 全XX巻 のような表記を削除
    title = re.sub(r'全\d+巻', '', title)
    # 末尾の空白を整理
    return title.strip()


# APIクライアントの準備（fetch_readings.pyと同じconfig読み込み）
from config import load_config
config = load_config()
api_key = config.get("gemini_api_key", "")
model = config.get("llm_model", "gemini-2.0-flash")

client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})

DELAY = 10.0
MAX_BATCH_SIZE = 180


def fetch_readings(client, model_name, titles: list) -> dict:
    """タイトルに対して読み方を取得"""
    titles_text = "\n".join(f"{i+1}. {t}" for i, t in enumerate(titles))
    prompt = f"""You are a Japanese reading assistant. For each manga title listed below, provide the hiragana reading (ふりがな).

RULES:
1. Return readings for ALL titles listed - do not skip any
2. Use ONLY hiragana (平仮名) for readings
3. If uncertain or ambiguous, use "unknown" as the reading
4. Return valid JSON only - no extra text

SPECIAL CONSIDERATIONS:
- Some titles may contain romanized text. Treat them as Japanese words and provide the standard Japanese reading.
- Some titles may include volume numbers or decorative symbols. Focus ONLY on the actual manga title.

TITLES:
{titles_text}

OUTPUT FORMAT:
{{"readings": {{"title1": "reading1", "title2": "reading2", ...}}}}"""

    response = client.models.generate_content(model=model_name, contents=prompt)
    text = response.text.strip()
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:-1]).strip()
        if text.startswith("json"):
            text = text[4:].strip()

    try:
        result = json.loads(text)
        return result
    except json.JSONDecodeError:
        # JSON抽出のフォールバック
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        return {"readings": {}}
    except Exception as e:
        print(f"    解析エラー: {e}")
        print(f"    raw: {text[:500]}")
        return {"readings": {}}


# バッチ作成
def split_batches(titles, max_size):
    batches = []
    for i in range(0, len(titles), max_size):
        batches.append(titles[i:i + max_size])
    return batches

batches = split_batches(failed_titles, MAX_BATCH_SIZE)

# A: 元タイトルでAPI評価
print("=" * 50)
print("=== A: 元タイトル（変換なし）でAPI評価 ===")
print("=" * 50)

success_a = 0
fail_a = 0
fail_list_a = []

for i, batch in enumerate(batches):
    print(f"\n--- バッチ {i+1}/{len(batches)} ({len(batch)}件) ---")
    result = fetch_readings(client, model, batch)
    readings = result.get("readings", {})
    for title in batch:
        if title in readings:
            success_a += 1
        else:
            fail_a += 1
            fail_list_a.append(title)
    time.sleep(DELAY)

print(f"\nA結果: 成功 {success_a}件 / 失敗 {fail_a}件 (計{len(failed_titles)}件)")
print(f"成功率: {success_a / len(failed_titles) * 100:.1f}%")

# B: 変換後タイトルでAPI評価
print()
print("=" * 50)
print("=== B: 簡略化後タイトルでAPI評価 ===")
print("=" * 50)

success_b = 0
fail_b = 0
fail_list_b = []

for i, batch in enumerate(batches):
    simplified_batch = [simplify_title(t) for t in batch]
    print(f"\n--- バッチ {i+1}/{len(batches)} ({len(simplified_batch)}件) ---")
    result = fetch_readings(client, model, simplified_batch)
    readings = result.get("readings", {})
    for orig_title, simp_title in zip(batch, simplified_batch):
        if simp_title in readings:
            success_b += 1
        else:
            fail_b += 1
            fail_list_b.append(orig_title)
    time.sleep(DELAY)

print(f"\nB結果: 成功 {success_b}件 / 失敗 {fail_b}件 (計{len(failed_titles)}件)")
print(f"成功率: {success_b / len(failed_titles) * 100:.1f}%")

# 結果比較
print()
print("=" * 50)
print("=== 結果比較 ===")
print("=" * 50)
print(f"A (元タイトル)    : {success_a}/{len(failed_titles)}件  ({success_a / len(failed_titles) * 100:.1f}%)")
print(f"B (簡略化後)      : {success_b}/{len(failed_titles)}件  ({success_b / len(failed_titles) * 100:.1f}%)")
diff = success_b - success_a
print(f"改善差: {'+' if diff >= 0 else ''}{diff}件")

# Bで成功したけどAで失敗したタイトルの例
only_b_success = set()
for title in fail_list_a:
    simp = simplify_title(title)
    if title not in fail_list_b:
        only_b_success.add(title)

if only_b_success:
    print(f"\n--- 簡略化で改善されたタイトルの例 (計{len(only_b_success)}件) ---")
    for t in sorted(list(only_b_success)[:10]):
        print(f"  元:   {t}")
        print(f"  変換: {simplify_title(t)}")
        print()
