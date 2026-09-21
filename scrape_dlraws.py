"""
dl-raw.si からマンガタイトルを取得して重複削除したリストを作成する
"""
import re
import time
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

BASE_URL = "https://dl-raw.si/category/manga/page/{page}/"
TOTAL_PAGES = 2149
OUTPUT_FILE = "dl_raw_titles.txt"

session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries))
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
})

titles = set()
last_report = time.time()

print(f"スクレイピング開始... (合計{TOTAL_PAGES}ページ)")

for page in range(1, TOTAL_PAGES + 1):
    now = time.time()
    if now - last_report > 15:
        print(f"  進行中: {page}/{TOTAL_PAGES}ページ | タイトル数: {len(titles)}")
        last_report = now

    try:
        resp = session.get(BASE_URL.format(page=page), timeout=30)
        content = resp.text

        # "Category: マンガ" 以降 "Previous" 以前の部分を取得
        section_match = re.search(r'Category:\s*マンガ\s*(.*?)Previous', content, re.DOTALL)
        if not section_match:
            continue

        section = section_match.group(1)

        # h2タグ内のaタグのtitle属性からタイトルを抽出
        for m in re.finditer(r'<a[^>]*title="([^"]+)"', section):
            raw_title = m.group(1)
            # "raw 第xx巻" 部分を削除して純粋なタイトルを得る
            clean_title = re.sub(r'\s*raw\s*第[^\s"]*$', '', raw_title, flags=re.IGNORECASE).strip()
            # "raw" だけでも削除（巻数が指定されていないものも）
            clean_title = re.sub(r'\s*raw\s*$', '', clean_title, flags=re.IGNORECASE).strip()
            if clean_title and len(clean_title) > 1:
                titles.add(clean_title)

        time.sleep(0.8)

    except Exception as e:
        print(f"  ⚠ ページ{page}エラー: {e}")
        time.sleep(2)

# 結果を保存
sorted_titles = sorted(titles)
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    for t in sorted_titles:
        f.write(t + "\n")

print(f"\n✅ 完了！ {len(sorted_titles)}件のタイトルを {OUTPUT_FILE} に保存しました")