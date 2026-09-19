# TEST.md — 5ステップパイプラインの動作テスト計画

## 概要

5ステップ構成の読み方取得パイプラインを10%サブセットデータで全ステップ検証し、
生成データの正誤評価方法も含めてテストを行う。

---

## 1. テスト環境準備

### 1.1 データ準備
- **バックアップ:** `cleaned_titles.json.bak` に元データをコピー
- **サブセット生成:** 先頭 ~4,085 件（10%）を `cleaned_titles.json` に書き込み
- **新規タイトル:** `new_test_titles.txt` を作成（~15件、既存に重複しないタイトル）
- **正解データ:** `ground_truth.json` を作成（~30件、既知の正解読み方）

### 1.2 環境変数
- `GOOGLE_API_KEY` が設定済みであることを確認

### 1.3 DB状態
- テスト実行前の `manga_titles.db` 行数を記録
- テスト後に差分（追加行数）を確認

---

## 2. テスト実行フロー

```
1. cleaned_titles.json → バックアップ
2. サブセット（~4,085件）で cleaned_titles.json を上書き
3. new_test_titles.txt を配置
4. ground_truth.json を配置
5. python run_pipeline.py --steps 1,2,3,4,5
6. python validate_readings.py（正誤検証）
7. 結果レポートを出力
8. バックアップからリストア
```

---

## 3. 正誤評価方法

| レベル | 検証内容 | 方法 | 実施スクリプト |
|--------|---------|------|----------------|
| **L1: フォーマットチェック** | ひらがなのみか？空文字列入っていないか？ | 正規表現 `^[ぁ-ん]+$` で全件チェック | `validate_readings.py` |
| **L2: 既知データ比較** | 正解データとの一致率 | `ground_truth.json` とDB結果を比較 | `validate_readings.py` |
| **L3: 二重判定（オプション）** | 別のAPIで同じ結果か？ | サンプリングでOpenAI等と比較 | 別途実装 |
| **L4: 人手チェック** | ランダムサンプルの人手確認 | 10~20件を人手で確認 | 最終品質保証 |

---

## 4. 期待される出力・検証ポイント

| スクリプト | 出力ファイル | 検証項目 |
|-----------|-------------|---------|
| `clean_titles.py` | `cleaned_titles.json` | ~4,085件の一意タイトルが入っている |
| `group_titles.py` | `batch_groups.json` | 約23グループで再生成されている |
| `fetch_readings.py` | `manga_titles.db` | DB行数がテスト分だけ増加している |
| `export_results.py` | `readings_success.csv`, `failed_titles.txt` | ファイルが生成され、行数が合っている |
| `add_new_titles.py` | 更新済 `cleaned_titles.json` | ~15件の新規タイトルが追加されている |
| `validate_readings.py` | `validation_report.json` | L1,L2のスコアが出力されている |

---

## 5. 判定基準

- **フォーマット:** L1チェックの合格率 ≥ 95%
- **精度:** L2一致率 ≥ 80%（Gemini flashの特性を考慮）
- **完了:** 5ステップがすべて exit code 0 で終了

---

## 6. ファイル構成

```
FindMangaTitle/
├── validate_readings.py    # 新規作成予定（L1+L2検証）
├── ground_truth.json       # 新規作成予定（正解データ）
├── new_test_titles.txt     # 新規作成予定（テスト用新規タイトル）
├── validation_report.json  # validate_readings.pyの出力
└── TEST.md                 # 本ファイル
```