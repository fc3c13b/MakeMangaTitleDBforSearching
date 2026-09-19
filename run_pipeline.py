"""
run_pipeline.py - 5ステップの読み方取得パイプラインをオーケストレート

Steps:
  1. clean_titles.py      - タイトル簡略化・重複削除
  2. group_titles.py      - APIバッチンググルーピング
  3. fetch_readings.py    - APIフェッチ & DB格納
  4. export_results.py    - CSV/TXTエクスポート
  5. add_new_titles.py    - 新規タイトル追加

使用例:
  # フルパイプライン実行
  python run_pipeline.py

  # 一部のステップのみ
  python run_pipeline.py --steps 3
  python run_pipeline.py --steps 1,2,3

  # Step 3 (--start/--end) のオプション変更
  python run_pipeline.py --steps 3 --fetch-args '--start 100 --end 110'
"""

import os
import sys
import argparse
import subprocess

# 各ステップのスクリプト名
SCRIPTS = {
    1: "clean_titles.py",
    2: "group_titles.py",
    3: "fetch_readings.py",
    4: "export_results.py",
    5: "add_new_titles.py",
}

STEP_LABELS = {
    1: "タイトル簡略化・重複削除",
    2: "APIバッチンググルーピング",
    3: "APIフェッチ & DB格納",
    4: "CSV/TXTエクスポート",
    5: "新規タイトル追加",
}


def run_step(step_id: int, extra_args: str = "", cwd: str = None):
    """1つのステップを実行"""
    script = SCRIPTS[step_id]
    cmd = [sys.executable, script]
    if extra_args:
        cmd.extend(extra_args.split())
    
    label = STEP_LABELS[step_id]
    print(f"\n{'='*60}")
    print(f"Step {step_id}/5: {label}")
    print(f"{'='*60}")
    print(f"コマンド: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"[エラー] {script} が失敗しました (exit code: {result.returncode})")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(
        description="5ステップの読み方取得パイプライン",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--steps", type=str, default="1,2,3,4,5",
        help="実行するステップ (カンマ区切り, default: 1,2,3,4,5)"
    )
    parser.add_argument(
        "--fetch-args", type=str, default="",
        help="Step 3 (--start/--end等) のオプション文字列"
    )
    
    args = parser.parse_args()
    
    # ステップIDリストをパース
    try:
        steps = [int(s.strip()) for s in args.steps.split(",")]
    except ValueError:
        print("エラー: --steps はカンマ区切りの数字を指定してください (例: 1,2,3)")
        sys.exit(1)
    
    steps.sort()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("="*60)
    print("  読み方取得パイプライン")
    print("="*60)
    print(f"実行ステップ: {steps}")
    print(f"Step 3追加引数: {args.fetch_args or '(none)'}")
    
    for step_id in steps:
        if step_id not in SCRIPTS:
            print(f"未定義のステップ: {step_id}。指定可能な値: {list(SCRIPTS.keys())}")
            sys.exit(1)
        
        extra = args.fetch_args if step_id == 3 else ""
        if not run_step(step_id, extra_args=extra, cwd=base_dir):
            print(f"\nStep {step_id} でエラーが発生しました。中止します。")
            sys.exit(1)
    
    print(f"\n{'='*60}")
    print("  パイプライン完了!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

