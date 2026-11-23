"""Check a saved extraction and render the result."""

import argparse
import json
from pathlib import Path

from .core import check, read_json


def render(result):
    labels = {"conflict": "衝突候補あり", "incomplete": "未変換箇所あり", "no_candidate": "モデル内で候補なし"}
    print(f'{labels[result["status"]]}（変換済みのルール {result["rule_count"]} 件）')
    for finding in result["conflicts"]:
        witness = ", ".join(f"{key}={value}" for key, value in finding["witness"].items())
        print(f'\n行動 {finding["action"]} / 状況 {witness or "条件なし"}')
        for role, name in (("required", "必須"), ("forbidden", "禁止")):
            for line in finding[role]["source"]:
                print(f'  {name} [{line["id"]}] {line["text"]}')
        print('  ' + finding["reason"])
    if result["unmodeled"]:
        print("\n未変換箇所")
        for gap in result["unmodeled"]:
            for line in gap["source"]:
                print(f'  [{line["id"]}] {line["text"]}')
            print('  理由: ' + gap["reason"])


def main():
    parser = argparse.ArgumentParser(description="構造化したプロンプト指示の衝突を検査します")
    parser.add_argument("prompt", type=Path, help="行に [R01] 形式の目印を付けた原文")
    parser.add_argument("model", type=Path, help="抽出結果のJSON")
    parser.add_argument("--json", action="store_true", help="JSONで出力する")
    args = parser.parse_args()
    try:
        result = check(args.prompt.read_text(encoding="utf-8"), read_json(args.model))
    except (OSError, ValueError) as error:
        parser.error(str(error))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        render(result)


if __name__ == "__main__":
    main()
