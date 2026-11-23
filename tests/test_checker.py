"""Check model validation, symbolic witnesses and the bundled experiments."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from checker.authority import check_authority
from checker.constraints import analyze
from checker.core import check, read_json
from examples.__main__ import evaluate, run

ROOT = Path(__file__).resolve().parents[1]


def rule(index, effect, *, when=None, unless=None, action="attach_link"):
    return {
        "id": f"rule{index}", "sources": [f"R{index:02}"], "effect": effect,
        "action": action, "when": when or {}, "unless": unless or [],
    }


class PairCheckTests(unittest.TestCase):
    prompt = "# 配送対応\n[R01] 追跡ページを案内する。\n[R02] 追跡ページを案内しない。\n"
    model = {
        "context": {"sent": ["yes", "no"], "address_known": ["yes", "no"], "source": ["web", "phone"]},
        "rules": [rule(1, "require", when={"sent": "yes"}, unless=[{"address_known": "no"}]),
                  rule(2, "forbid", when={"source": "phone"})],
        "unmodeled": [],
    }

    def test_witness_obeys_both_conditions_and_exception(self):
        result = check(self.prompt, self.model)
        finding, = result["conflicts"]
        self.assertEqual(finding["witness"], {"sent": "yes", "address_known": "yes", "source": "phone"})
        self.assertEqual(finding["required"]["source"], [{"id": "R01", "text": "追跡ページを案内する。"}])

    def test_conditions_exclude_one_another(self):
        rules = [rule(1, "require", when={"sent": "yes"}), rule(2, "forbid", when={"sent": "no"})]
        self.assertEqual(check(self.prompt, dict(self.model, rules=rules))["status"], "no_candidate")

    def test_all_overlapping_states_are_exempt(self):
        rules = [rule(1, "require", unless=[{"source": "phone"}, {"source": "web"}]), rule(2, "forbid")]
        self.assertEqual(check(self.prompt, dict(self.model, rules=rules))["status"], "no_candidate")

    def test_missing_traceability_fails_validation(self):
        with self.assertRaisesRegex(ValueError, "対応していない"):
            check(self.prompt, dict(self.model, rules=self.model["rules"][:1]))

    def test_unknown_condition_value_fails_validation(self):
        rules = [rule(1, "require", when={"sent": "maybe"}), rule(2, "forbid")]
        with self.assertRaisesRegex(ValueError, "context にない"):
            check(self.prompt, dict(self.model, rules=rules))

    def test_duplicate_json_key_fails_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "model.json"
            file.write_text('{"context": {}, "context": []}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "重複キー"):
                read_json(file)

    def test_actual_cli_with_utf8_input(self):
        result = subprocess.run(
            [sys.executable, "-m", "checker", "examples/prompts/m03.md", "examples/extracted/m03.json", "--json"],
            cwd=ROOT, capture_output=True, check=True, text=True, encoding="utf-8",
        )
        decoded = json.loads(result.stdout)
        self.assertEqual(decoded, run("m03"))
        self.assertEqual(decoded["status"], "conflict")

    def test_visible_gaps_can_coexist_with_a_candidate(self):
        prompt = self.prompt + "[R03] なるべく気楽な文章にする。\n"
        result = check(prompt, dict(self.model, unmodeled=[{"sources": ["R03"], "reason": "主観的な指示"}]))
        self.assertEqual(result["status"], "conflict")
        self.assertEqual(result["unmodeled"][0]["source"][0]["id"], "R03")


class EvaluationTests(unittest.TestCase):
    def test_expected_labels_on_all_saved_extractions(self):
        rows = evaluate()
        self.assertEqual(len(rows), 24)
        for row in rows:
            with self.subTest(case=row["case"]):
                self.assertEqual(row["observed"], row["expected"])

    def test_independent_extractions_preserve_conflict_source_pairs(self):
        for case in ("s1", "m03", "m05", "a1"):
            with self.subTest(case=case):
                def source_pairs(result):
                    return [(r["required"]["source"][0]["id"], r["forbidden"]["source"][0]["id"])
                            for r in result["conflicts"]]
                self.assertEqual(source_pairs(run(case)), source_pairs(run(case, "repeated")))


class AdvancedTests(unittest.TestCase):
    def test_constraints_and_removal_witnesses(self):
        cases = read_json(ROOT / "experiments/constraints.json")
        expected = {
            "a4": ["R01", "R02", "R03"],
            "a5": ["R01", "R02", "R03", "assumption_disjoint_examples"],
            "a6": ["R01", "R02"],
        }
        for name, core in expected.items():
            with self.subTest(case=name):
                case = cases[name]
                result = analyze(case)
                self.assertEqual(result["status"], "unsatisfiable_in_domain")
                self.assertEqual(result["unsat_core"], core)
                for removed, witness in result["removal_witnesses"].items():
                    domains = {key: values if isinstance(values, list) else {"min": witness[key], "max": witness[key]}
                               for key, values in case["domains"].items()}
                    narrowed_rules = [r for r in case["constraints"] if r["id"] != removed]
                    # Pin Boolean variables with independent extra constraints.
                    narrowed_rules.extend(
                        {"id": f"pin_{key}", "expression": key if witness[key] else ["not", key]}
                        for key, values in domains.items() if isinstance(values, list)
                    )
                    self.assertEqual(analyze({"domains": domains, "constraints": narrowed_rules})["witness"], witness)

    def test_authority_depends_on_source_and_quotation_metadata(self):
        cases = read_json(ROOT / "experiments/authority.json")
        self.assertEqual(
            {name: check_authority(case) for name, case in cases.items()},
            {"reference_directive": "unauthorized_instruction", "reference_quotation": "quoted_content",
             "policy_directive": "authorized", "user_summary": "authorized"},
        )


if __name__ == "__main__":
    unittest.main()
