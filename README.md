# MakeMangaTitleDBforSearching — 漫画タイトル自動識別ツール

[Gemini AI API](https://ai.google.dev/gemini-api) を使って、ダウンロードした漫画のフォルダ名（生タイトル）の読み方（ふりがな）を自動取得し、SQLiteにDB化するバッチ処理パイプラインです。

---

## 処理フロー（5ステップ）

```
┌──────────────────┐      ┌──────────────────┐
│ dl_raw_titles.txt │ ──→ │ cleaned_titles.json│
│ （生タイトルリスト） │     │（簡略化・重複削除） │
└──────────────────┘      └──────────────────┘
                                               │
                                               ↓
                                 ┌──────────────────┐
                                 │ batch_groups.json │
                                 │（APIバッチング用） │
                                 └──────────────────┘
                                               │
                                               ↓
                                 ┌──────────────────┐
                                 │ manga_titles.db   │
                                 │（読み方取得・DB化）│
                                 └──────────────────┘
                                               │
                                               ↓
┌──────────────────┐      ┌──────────────────┐
│readings_success. │      │ failed_titles.txt │
│     csv          │      │（失敗タイトル一覧）  │
└──────────────────┘      └──────────────────┘
```

| ステップ | スクリプト | 説明 | 入出力 |
|---------|-----------|------|--------|
| 1 | `clean_titles.py` | タイトル整理・重複削除 | `dl_raw_titles.txt` → `cleaned_titles.json` |
| 2 | `group_titles.py` | API処理用のバッチグルーピング | `cleaned_titles.json` → `batch_groups.json` |
| 3 | `fetch_readings.py` | Gemini APIで読み方取得・DB化 | `batch_groups.json` → `manga_titles.db` |
| 4 | `export_results.py` | 成功/失敗タイトルのテキスト化 | → `readings_success.csv`, `failed_titles.txt` |
| 5 | `add_new_titles.py` | 新規タイトルの重複チェック・追加 | `dl_raw_titles.txt` → `cleaned_titles.json` (追加) |

---

## 使用方法

### セットアップ

```bash
pip install -r requirements.txt
```

`.env`ファイルにAPIキーを記載：
```
GEMINI_API_KEY=your_api_key_here
```

### 全パイプライン実行

```bash
python run_pipeline.py
```

### 個別ステップ実行

```bash
# ステップ1: タイトル整理・重複削除
python clean_titles.py

# ステップ2: APIバッチング用グルーピング
python group_titles.py

# ステップ3: 読み方取得・DB化
python fetch_readings.py

# ステップ4: 成功/失敗タイトルのテキスト化
python export_results.py

# ステップ5: 新規タイトルの重複チェック・追加
python add_new_titles.py
```

---

## 出力フォーマット

### cleaned_titles.json

```json
[
  {"id": 0, "title": "ナルト"},
  {"id": 1, "title": "ワンパンマン"},
  ...
]
```

### batch_groups.json

```json
[
  {
    "group_id": 0,
    "titles": ["title1", "title2", ...]
  },
  ...
]
```

### readings_success.csv

```
title,reading,source,confidence
ナルト,なると,llm_reading,1.0
```

---

## ファイル構成

| ファイル | 説明 |
|---------|------|
| `clean_titles.py` | タイトル整理・重複削除（ステップ1） |
| `group_titles.py` | APIバッチング用グルーピング（ステップ2） |
| `fetch_readings.py` | Gemini APIで読み方取得・DB化（ステップ3） |
| `export_results.py` | 成功/失敗タイトルのテキスト化（ステップ4） |
| `add_new_titles.py` | 新規タイトル重複チェック・追加（ステップ5） |
| `run_pipeline.py` | 全ステップ統合実行 |
| `config.py` | 設定・APIキー定義 |
| `database.py` | SQLite DB操作モジュール |

---

## 簡略化ルール（ステップ1）

以下のパターンを正規表現で削除します：

- `[Romaji]` 形式の括弧（例: `[One Piece vol 01]`）
- 巻番号（例: `第01-02巻`, `第01巻`, `全45巻`）
- `raw 全03巻` 等の raw フォーマット
- `上下巻` 表記

---

## 注意事項

- Gemini API のレートリミットに注意してください（バッチ処理・待機時間を含んでいます）
- 処理には時間がかかります（数百〜数千件の場合、数〜数十分）
- 中断時はチェックポイント機能が自動的に続きから処理を開始します