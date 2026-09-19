# TASK.md — 現在の課題

## 概要
`fetch_readings.py` を5つのスクリプトに分割し、README.mdで定義した5ステップ構成に合わせる。

---

## 完了済み

- [x] README.md を5ステップ構成に更新
- [x] group_titles.py を新規作成 (Step 2)
- [x] export_results.py を新規作成 (Step 4)

---

## 未完了タスク

### 1. `group_titles.py` を新規作成
- `fetch_readings.py`内の `split_titles_by_char_limit()` を独立させる
- 入力: `cleaned_titles.json` → 出力: `batch_groups.json`

### 2. `export_results.py` を新規作成
- `fetch_readings.py`内のCSV/TXT出力部分を独立させる
- 入力: API処理結果 → 出力: `readings_success.csv`, `failed_titles.txt`

### 3. `add_new_titles.py` を新規作成
- 新規タイトルを既存 `cleaned_titles.json` に重複チェックして追加する機能

### 4. `fetch_readings.py` を縮小
- グルーピング処理とエクスポート処理を削除
- 純粋なAPI呼び出し・DB保存のみを残す

### 5. `run_pipeline.py` を更新
- 旧3ステップ（Media Arts DB参照）→ 新5ステップ構成に更新
