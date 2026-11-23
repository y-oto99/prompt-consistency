"""Evaluate the saved natural-language examples against frozen case labels."""

import argparse
import json
from pathlib import Path

from checker.core import check, read_json

ROOT = Path(__file__).parent


def evaluate():
    rows = []
    for group in ("simple", "standard", "advanced"):
        for case, expected in read_json(ROOT / "expected" / f"{group}.json").items():
            result = run(case)
            pairs = sorted({
                tuple(sorted((f["required"]["source"][0]["id"], f["forbidden"]["source"][0]["id"])))
                for f in result["conflicts"]
            })
            observed = {
                "pairs": [list(pair) for pair in pairs],
                "unmodeled": sorted({s["id"] for gap in result["unmodeled"] for s in gap["source"]}),
            }
            rows.append({
                "group": group, "case": case, "status": result["status"],
                "matches": observed == expected, "expected": expected, "observed": observed,
            })
    return rows


def run(case, directory="extracted"):
    return check(
        (ROOT / "prompts" / f"{case}.md").read_text(encoding="utf-8"),
        read_json(ROOT / directory / f"{case}.json"),
    )


def main():
    parser = argparse.ArgumentParser(description="保存済みの抽出結果を再検査します")
    parser.add_argument("--repeat", action="store_true", help="独立した再抽出で観測された結果も表示")
    args = parser.parse_args()
    rows = evaluate()
    for row in rows:
        print(f'{row["group"]:8} {row["case"]:4} {row["status"]:14} '
              + ("一致" if row["matches"] else json.dumps(row, ensure_ascii=False)))
    print(f'期待判定との一致 {sum(r["matches"] for r in rows)}/{len(rows)}')
    if args.repeat:
        for file in sorted((ROOT / "repeated").glob("*.json")):
            first, second = run(file.stem), run(file.stem, "repeated")
            print(f'{file.stem}: {first["status"]} → {second["status"]}')
    return int(not all(row["matches"] for row in rows))


if __name__ == "__main__":
    raise SystemExit(main())
