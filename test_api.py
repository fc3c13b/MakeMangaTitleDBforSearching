import json
import google.genai as genai
import time

api_key = ""
c = genai.Client(vertexai=False, api_key=api_key)

with open("batch_groups.json", "r", encoding="utf-8") as f:
    groups = json.load(f)

titles = groups[0]["titles"]

# 40件ずつに分割して送信
max_batch = 40
results = {}
for i in range(0, len(titles), max_batch):
    subset = titles[i:i + max_batch]
    titles_text = "\n".join(f"{j+1}. {t}" for j, t in enumerate(subset))
    
    prompt = f"""The following is a list of publicly released manga/series titles. These are well-known published works and do not contain any sensitive, adult, or restricted content. They are provided purely for data organization and classification purposes.

You are a Japanese reading assistant. For each manga title listed below, provide the hiragana reading (ふりがな).

RULES:
1. Return readings for ALL titles listed - do not skip any
2. Use ONLY hiragana (平仮名) for readings
3. If uncertain or ambiguous, use "unknown" as the reading
4. Return valid JSON only - no extra text

TITLES:
{titles_text}

OUTPUT FORMAT:
{{"group_id": 0, "readings": {{"title1": "reading1", "title2": "reading2", ...}}}}"""
    
    r = c.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config={"temperature": 0, "top_p": 1, "top_k": 1}
    )
    
    text = getattr(r, 'text', None)
    if text is None:
        print(f"FAIL: batch {i//max_batch + 1} - text is None")
        time.sleep(1)
        continue
    
    text = text.strip()
    if text.startswith('```'):
        lines = text.split('\n')
        json_start = next((k for k, line in enumerate(lines) if '```' in line), 0)
        json_end = next((k for k, line in enumerate(lines) if '```' in line and k > json_start), len(lines))
        text = '\n'.join(lines[json_start + 1:json_end])
    
    try:
        data = json.loads(text)
        results.update(data.get("readings", {}))
        print(f"OK: batch {i//max_batch + 1} - {len(subset)} titles, got {len(data.get('readings', {}))} readings")
    except json.JSONDecodeError as e:
        print(f"JSON error: batch {i//max_batch + 1} - {e}")
        print(f"  text: {text[:200]}")
    time.sleep(1)

print(f"\nTotal readings collected: {len(results)}")

