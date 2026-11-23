"""Independent checks of the formal engines and representative policy decisions."""

from itertools import product
import unittest

from checker.boundary import assess
from checker.interpretations import check_readings
from checker.workflow_model import PROPERTIES, PROTOCOLS, State, model_check, transitions
from validation.__main__ import boundary_report, compare
from validation.boundary_cases import cases
from validation.boundary_model import explore


def literal(action, effect):
    return {"action": action, "effect": effect}


def clause(line, *literals):
    return {"line": line, "any_of": list(literals)}


def reading(*constraints, gap=None):
    return {"note": "A reading", "constraints": list(constraints), "relevant_gap": gap}


class InterpretationTest(unittest.TestCase):
    sources = {"a": "at least one", "b": "no tea", "c": "no milk"}
    choice = clause("a", literal("tea", "do"), literal("milk", "do"))
    no_tea = clause("b", literal("tea", "omit"))
    no_milk = clause("c", literal("milk", "omit"))

    def test_distinct_readings_report_conflict_and_witness(self):
        result = check_readings(
            [reading(self.choice, self.no_tea, self.no_milk), reading(self.choice, self.no_tea)], self.sources
        )
        self.assertEqual(result["status"], "interpretation_dependent")
        negative, positive = result["readings"]
        self.assertEqual(negative["conflict_lines"], ["a", "b", "c"])
        self.assertEqual(positive["response_witness"], {"milk": True, "tea": False})

    def test_all_small_constraints_against_systematic_truth_table(self):
        literals = [literal(action, effect) for action, effect in product(("tea", "milk"), ("do", "omit"))]
        choices = [(l,) for l in literals] + list(product(literals, repeat=2))
        assignments = list(dict(zip(("tea", "milk"), values)) for values in product((False, True), repeat=2))
        for first, second in product(choices, repeat=2):
            expected = any(
                all(any(a[l["action"]] == (l["effect"] == "do") for l in c) for c in (first, second))
                for a in assignments
            )
            case = check_readings([reading(clause("a", *first), clause("b", *second))], self.sources)
            self.assertEqual(case["status"], "compatible" if expected else "conflict")

    def test_unknown_semantics_prevent_unconditional_label(self):
        known = reading(self.choice, self.no_tea, self.no_milk)
        gap = reading(self.choice, self.no_tea, gap="unknown applicable exception")
        self.assertEqual(check_readings([known, gap], self.sources)["status"], "unresolved")

    def test_nonexistent_line_is_rejected(self):
        with self.assertRaises(ValueError):
            check_readings([reading(clause("hallucinated", literal("tea", "do")))], self.sources)

    def test_saved_extractions_have_valid_citations(self):
        self.assertEqual(len(compare()), 18)
        self.assertEqual(len(compare("holdout")), 6)


class WorkflowTest(unittest.TestCase):
    def test_only_queue_time_check_has_replayable_counterexamples(self):
        protocol = PROTOCOLS["queue_check_only"]
        result = model_check(protocol, 2)
        for property, evidence in result["properties"].items():
            self.assertFalse(evidence["holds"])
            state = State()
            for event in evidence["counterexample"]:
                state = dict(transitions(state, protocol, 2))[event]
            self.assertFalse(PROPERTIES[property](state))

    def test_revision_check_alone_misses_revocation(self):
        result = model_check(PROTOCOLS["bind_revision"], 2)
        self.assertTrue(result["properties"]["published_approved_revision"]["holds"])
        self.assertFalse(result["properties"]["publication_has_active_approval"]["holds"])

    def test_safety_and_recovery_both_matter(self):
        for bound in (2, 3, 4):
            complete = model_check(PROTOCOLS["guarded"], bound)
            stranded = model_check(PROTOCOLS["guarded_without_recovery"], bound)
            self.assertTrue(all(p["holds"] for p in complete["properties"].values()))
            self.assertTrue(complete["completion_possible_from_all_states"])
            self.assertTrue(complete["published_example"])
            self.assertTrue(all(p["holds"] for p in stranded["properties"].values()))
            self.assertFalse(stranded["completion_possible_from_all_states"])
            self.assertTrue(stranded["stranded_trace"])


class BoundaryTest(unittest.TestCase):
    def test_reference_as_data_and_missing_request_provenance(self):
        records = cases()
        for key, decision in [
            ("summary_with_quoted_direction_in_reference", "allow"),
            ("tool_result_as_request_origin", "deny"),
            ("missing_origin", "review"),
        ]:
            self.assertEqual(assess(records[key][0])[0], decision)

    def test_approval_subject_revision_and_audience_are_bound(self):
        records = cases()
        for key, reason in [
            ("intent_changes_subject", "proposal_differs_from_confirmed_intent"),
            ("intent_changes_audience", "proposal_differs_from_confirmed_intent"),
            ("proposal_old_version", "stale_revision"),
            ("approval_old_version", "approval_bound_to_different_effect"),
            ("approval_revoked", "no_active_approval"),
        ]:
            self.assertEqual(assess(records[key][0]), ("deny", reason))


    def test_only_allowed_effects_pass_for_finite_host_metadata(self):
        result = explore()
        self.assertEqual(result["combinations"], 10080)
        self.assertGreater(result["allowed"], 0)
        self.assertIsNone(result["first_violation"])

    def test_policy_matches_defensive_fixtures(self):
        result = boundary_report()
        self.assertEqual(result["bound_effect"]["counts"].get("matched_expected"), len(cases()))
        self.assertGreater(result["operation_only"]["counts"]["unexpected_allow"], 0)


if __name__ == "__main__":
    unittest.main()
