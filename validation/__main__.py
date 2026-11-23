"""Reproduce fixed-scenario evaluation, workflow model checking and defense tests."""

import argparse
from collections import Counter
import json
import sys
from pathlib import Path

from checker.boundary import assess
from checker.core import read_json
from checker.interpretations import check_readings
from checker.workflow_model import PROTOCOLS, model_check
from .boundary_cases import DESCRIPTIONS, cases as boundary_cases
from .boundary_model import explore
from .build_inputs import passages, prompt_for

ROOT = Path(__file__).parent


def compare(dataset="development"):
    if dataset == "holdout":
        cases = read_json(ROOT / "holdout.json")
        expected = read_json(ROOT / "holdout_expected.json")
        extractions = {"revised": read_json(ROOT / "extractions" / "holdout.json")}
        direct = None
    elif dataset == "development":
        cases = read_json(ROOT / "cases.json")
        expected = read_json(ROOT / "expected.json")
        direct = read_json(ROOT / "extractions" / "direct.json")
        first = {}
        for name in ("controlled", "realistic"):
            for key, readings in read_json(ROOT / "extractions" / f"{name}.json").items():
                if key in first:
                    raise ValueError(f"duplicate case {key}")
                first[key] = readings
        extractions = {"initial": first, "revised": read_json(ROOT / "extractions" / "revised.json")}
    else:
        raise ValueError("unknown dataset")
    inventories = [expected] + list(extractions.values())
    if direct is not None:
        inventories.append(direct)
    if any(cases.keys() != other.keys() for other in inventories):
        raise ValueError("case inventories do not match")

    report = {}
    for key, case in cases.items():
        source = passages(prompt_for(case))
        report[key] = {
            "scope": case.get("scale", "workflow_prompt"),
            "source_chars": sum(map(len, source.values())),
            "source_lines": len(source),
            "situation": case["situation"],
            "expected": expected[key],
            "structured": {round_name: check_readings(values[key], source)
                           for round_name, values in extractions.items()},
        }
        if direct is not None:
            report[key]["direct"] = direct[key]
    return report

def boundary_report():
    result = {}
    fixtures = boundary_cases()
    for strategy in ("channel_only", "operation_only", "bound_effect"):
        rows = {}
        for name, (record, expected) in fixtures.items():
            decision, reason = assess(record, strategy)
            rows[name] = {"case": DESCRIPTIONS[name], "expected": expected,
                          "decision": decision, "reason": reason}
        flags = Counter()
        for row in rows.values():
            if row["decision"] == "allow" and row["expected"] != "allow":
                flags["unexpected_allow"] += 1
            if row["decision"] != "allow" and row["expected"] == "allow":
                flags["unexpected_block"] += 1
            flags["matched_expected"] += int(row["decision"] == row["expected"])
        result[strategy] = {"counts": dict(flags), "cases": rows}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", choices=("language", "holdout", "workflow", "boundary", "boundary-model", "prompt"))
    parser.add_argument("--bound", type=int, default=2, help="workflow maximum revision (1–4)")
    parser.add_argument("--case", help="case ID for the prompt command")
    args = parser.parse_args()
    if args.suite == "prompt":
        cases = read_json(ROOT / "cases.json") | read_json(ROOT / "holdout.json")
        if args.case not in cases:
            parser.error("prompt requires a valid --case")
        case = cases[args.case]
        sys.stdout.write(prompt_for(case) + "\n入力状況（プロンプトとは別）\n" + case["situation"] + "\n")
        return
    if args.suite == "language":
        output = compare()
    elif args.suite == "holdout":
        output = compare("holdout")
    elif args.suite == "workflow":
        output = {name: model_check(protocol, args.bound) for name, protocol in PROTOCOLS.items()}
    elif args.suite == "boundary-model":
        output = explore()
    else:
        output = boundary_report()
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
