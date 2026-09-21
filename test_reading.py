"""
test_reading.py - AI APIでタイトル読み方を調べるテストスクリプト
"""
import os
import json
from google import genai
from google.genai import types
from config import load_config

def get_api_key():
    """APIキーを取得する"""
    # config.json から取得
    config = load_config()
    if "gemini_api_key" in config:
        return config["gemini_api_key"]
    
    # 環境変数から取得
    api_key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
    return api_key


def main():
    # テスト用タイトル（dl_raw_titles.txtからサンプリング）
    test_titles = [
        "#34歳シェアハウスのオーナー始めます",
        "#DRCL midnight children",
        "#MeToo～AV出演を強要された私～",
        "#えあかつ 無名絵師からの絵垢活動記",
        "#こんなブラック・ジャックはイヤだ 第01-02巻",
        "#ふりむかないで#ふりむいて",
        "#オレ達飼われます",
        "#ゾンビさがしてます",
        "#バズゲーム",
        "#壊れた地球の歩き方",
        "#推しが俺様専属マネージャー",
        "#推しが幸せならOKです",
        "#神奈川に住んでるエルフ",
        "& 第01-08巻 [And vol 01-08]",
        "(仮)カレ！―年下カレシと秘密の関係―",
        "(仮)メイド喫茶マンドリル",
        "(元)ヤクザは紳士で猛獣 同棲したら秒で食べられちゃいました！",
        "(元)勇者と(次期)魔王の、魔王城までの歩き方",
    ]

    # APIキーを取得
    api_key = get_api_key()
    if not api_key:
        print("ERROR: APIキーが見つかりません。")
        print("config.jsonに 'gemini_api_key' を設定するか、")
        print("環境変数 GEMINI_API_KEY または GOOGLE_API_KEY を設定してください。")
        return

    # モデル名を取得
    config = load_config()
    model = config["llm_model"]
    print(f"モデル: {model}")
    print(f"テスト対象タイトル数: {len(test_titles)}")
    print()

    # Gemini APIクライアントを作成
    client = genai.Client(api_key=api_key)

    # プロンプトを作成
    titles_text = "\n".join(f"{i+1}. {t}" for i, t in enumerate(test_titles))
    prompt = f"""以下の漫画タイトルの読み方（ふりがな）を教えてください。
JSON形式で返してください。

タイトルリスト:
{titles_text}

出力形式:
{{
  "titles": [
    {{"title": "タイトル", "reading": "読み方"}},
    ...
  ]
}}"""

    # APIリクエスト
    print("APIリクエストを送信中...")
    response = client.models.generate_content(
        model=model,
        contents=prompt
    )

    # 結果を出力
    print("\n=== API応答 ===")
    print(response.text)
    print()

    # JSONパーステスト
    try:
        # 応答からJSON部分を抽出
        text = response.text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1]
        
        result = json.loads(text)
        print("=== パース成功 ===")
        for item in result.get("titles", []):
            print(f"{item['title']} -> {item['reading']}")
    except Exception as e:
        print(f"JSONパースエラー: {e}")


if __name__ == "__main__":
    main()