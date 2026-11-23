"""Run the finite constraint or authority examples and print the evidence."""

import argparse
import json
from pathlib import Path

from checker.authority import check_authority
from checker.constraints import analyze
from checker.core import read_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("family", choices=("constraints", "authority"))
    parser.add_argument("case", nargs="?")
    args = parser.parse_args()
    cases = read_json(Path(__file__).with_name(f"{args.family}.json"))
    if args.case:
        if args.case not in cases:
            parser.error(f"未知の事例です: {args.case}")
        cases = {args.case: cases[args.case]}
    run = analyze if args.family == "constraints" else check_authority
    print(json.dumps({name: run(case) for name, case in cases.items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
