"""Check disjunctions of actions for each reading of a fixed scenario."""

import re


def _solution(clauses, values=None):
    """Return one satisfying assignment, or None, by branching on a pending literal."""
    values = {} if values is None else values
    pending = []
    for clause in clauses:
        if any(action in values and values[action] == required for action, required in clause):
            continue
        available = [(action, required) for action, required in clause if action not in values]
        if not available:
            return None
        pending.append(available)
    if not pending:
        return values
    action, preferred = min(pending, key=len)[0]
    for choice in (preferred, not preferred):
        solution = _solution(pending, {**values, action: choice})
        if solution is not None:
            return solution
    return None


def _check_reading(reading, sources):
    if set(reading) != {"note", "constraints", "relevant_gap"} or not reading["note"].strip():
        raise ValueError("invalid reading")
    if reading["relevant_gap"] is not None and not reading["relevant_gap"].strip():
        raise ValueError("empty relevant_gap")
    constraints = reading["constraints"]
    if not isinstance(constraints, list) or len(constraints) > 48:
        raise ValueError("expected up to 48 constraints")
    clauses, lines = [], []
    for entry in constraints:
        if set(entry) != {"line", "any_of"} or entry["line"] not in sources:
            raise ValueError("a constraint needs a valid line reference")
        literals = []
        if not entry["any_of"] or len(entry["any_of"]) > 8:
            raise ValueError("expected 1–8 literals")
        for literal in entry["any_of"]:
            if (
                set(literal) != {"action", "effect"}
                or not re.fullmatch(r"[a-z][a-z0-9_]*", literal["action"])
                or literal["effect"] not in {"do", "omit"}
            ):
                raise ValueError("invalid action or effect")
            literals.append((literal["action"], literal["effect"] == "do"))
        clauses.append(literals)
        lines.append(entry["line"])
    actions = sorted({action for clause in clauses for action, _ in clause})
    if len(actions) > 20:
        raise ValueError("expected up to 20 actions per reading")
    solution = _solution(clauses)
    result = {"note": reading["note"], "gap": reading["relevant_gap"], "lines": sorted(set(lines))}
    if solution is not None:
        result["status"] = "unresolved" if reading["relevant_gap"] else "compatible"
        result["response_witness"] = {action: solution.get(action, False) for action in actions}
    else:
        core = [(line, clause) for line, clause in zip(lines, clauses)]
        for item in core[:]:
            rest = core.copy()
            rest.remove(item)
            if _solution([clause for _, clause in rest]) is None:
                core = rest
        # An extraction gap might hide an applicable exception.
        result["status"] = "unresolved" if reading["relevant_gap"] else "conflict"
        result["conflict_lines"] = sorted({line for line, _ in core})
    return result


def check_readings(readings, sources):
    """Condition conclusions on supplied readings and preserve mixed outcomes."""
    if not isinstance(readings, list) or not 1 <= len(readings) <= 8:
        raise ValueError("expected 1–8 readings")
    results = [_check_reading(reading, sources) for reading in readings]
    outcomes = {result["status"] for result in results}
    if {"conflict", "compatible"} <= outcomes:
        status = "interpretation_dependent"
    elif len(outcomes) == 1:
        status = outcomes.pop()
    else:
        status = "unresolved"
    return {"status": status, "readings": results}
