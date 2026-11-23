"""Bounded whole-set checking for small experimental constraint models."""

import itertools
import math
import operator

# An expression compiles to a type and a pure function of the variable assignment.
_OPERATORS = {
    "and": ((bool, bool), bool, operator.and_),
    "or": ((bool, bool), bool, operator.or_),
    "not": ((bool,), bool, operator.not_),
    "mul": ((int, int), int, operator.mul),
    "le": ((int, int), bool, operator.le),
    "lt": ((int, int), bool, operator.lt),
    "ge": ((int, int), bool, operator.ge),
}


def _compile(node, types):
    if type(node) in (bool, int):
        return type(node), lambda _: node
    if isinstance(node, str) and node in types:
        return types[node], lambda state: state[node]
    if not isinstance(node, list) or not node or not isinstance(node[0], str) or node[0] not in _OPERATORS:
        raise ValueError(f"不明な制約式です: {node}")
    inputs, output, op = _OPERATORS[node[0]]
    children = [_compile(arg, types) for arg in node[1:]]
    if tuple(kind for kind, _ in children) != inputs:
        raise ValueError(f"制約式の引数の個数または型が不正です: {node}")
    evaluators = [fn for _, fn in children]
    return output, lambda state: op(*(fn(state) for fn in evaluators))


def _domain(values):
    if isinstance(values, list) and values == [False, True] and all(type(v) is bool for v in values):
        return bool, tuple(values)
    if (
        isinstance(values, dict)
        and set(values) == {"min", "max"}
        and all(type(v) is int for v in values.values())
        and 0 <= values["max"] - values["min"] < 1_000_000
    ):
        return int, range(values["min"], values["max"] + 1)
    raise ValueError(f"値域は [false,true] または整数の min/max です: {values}")


def analyze(model):
    domains = {name: _domain(values) for name, values in model["domains"].items()}
    if math.prod(len(values) for _, values in domains.values()) > 1_000_000:
        raise ValueError("状態数の上限 1,000,000 を超えています")
    names = list(domains)
    identifiers = []
    constraints = []
    for rule in model["constraints"]:
        identifier = rule["id"]
        if not isinstance(identifier, str) or not identifier or identifier in identifiers:
            raise ValueError("制約のIDは一意な文字列で指定します")
        identifiers.append(identifier)
        kind, fn = _compile(rule["expression"], {name: domains[name][0] for name in names})
        if kind is not bool:
            raise ValueError(f"{identifier}: 制約の結果は真偽値でなければなりません")
        constraints.append(fn)
    if not constraints or len(constraints) > 12:
        raise ValueError("実験で扱う制約は1〜12件です")

    # Each mask records which requirements hold in one representative state.
    # One scan can then answer satisfiability for any subset of the requirements.
    states_examined = 0
    witnesses = {}
    full = (1 << len(constraints)) - 1
    for values in itertools.product(*(domains[name][1] for name in names)):
        states_examined += 1
        state = dict(zip(names, values))
        mask = sum(1 << i for i, predicate in enumerate(constraints) if predicate(state))
        if mask == full:
            return {"status": "satisfiable", "witness": state, "states_examined": states_examined}
        witnesses.setdefault(mask, state)

    def witness_for(subset):
        return next((state for mask, state in witnesses.items() if mask & subset == subset), None)

    core = full
    for index in range(len(constraints)):
        smaller = core & ~(1 << index)
        if witness_for(smaller) is None:
            core = smaller
    unsat_core = [r for i, r in enumerate(identifiers) if core & (1 << i)]
    return {
        "status": "unsatisfiable_in_domain",
        "states_examined": states_examined,
        "unsat_core": unsat_core,
        "removal_witnesses": {
            rule: witness_for(core & ~(1 << i))
            for i, rule in enumerate(identifiers) if core & (1 << i)
        },
    }
