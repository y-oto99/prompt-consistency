"""Finite overlap checks for explicitly modeled contexts and binary actions."""

import itertools
import json
import math
import re

IDENTIFIER = re.compile(r"[a-z][a-z0-9_]*")
SOURCE_LINE = re.compile(r"^\[(R[0-9]+)\][ \t]+(.+)$", re.MULTILINE)
MAX_CONTEXTS = 65_536


def read_json(path):
    def unique_keys(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"JSONに重複キーがあります: {key}")
            result[key] = value
        return result

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_keys)


def source_lines(prompt):
    matches = SOURCE_LINE.findall(prompt)
    result = dict(matches)
    if not result or len(matches) != len(result):
        raise ValueError("原文には一意な [R01] 形式の目印が必要です")
    return result


def _fields(record, fields, label):
    if not isinstance(record, dict) or set(record) != set(fields.split()):
        raise ValueError(f"{label} のフィールドは {fields} が必要です")


def _identifier(value):
    return isinstance(value, str) and IDENTIFIER.fullmatch(value) is not None


def _validate_sources(refs, lines, label):
    if (
        not isinstance(refs, list)
        or not refs
        or any(not isinstance(ref, str) or ref not in lines for ref in refs)
        or len(set(refs)) != len(refs)
    ):
        raise ValueError(f"{label}: sources には原文にある一意な行IDが必要です")


def _validate_condition(condition, context, label):
    if not isinstance(condition, dict):
        raise ValueError(f"{label}: 条件はオブジェクトで指定します")
    for key, value in condition.items():
        if key not in context or value not in context[key]:
            raise ValueError(f"{label}: context にない条件または値です: {key}={value}")


def validate(model, lines):
    _fields(model, "context rules unmodeled", "モデル")
    context = model["context"]
    if not isinstance(context, dict):
        raise ValueError("context はオブジェクトで指定します")
    for key, values in context.items():
        if (
            not _identifier(key)
            or not isinstance(values, list)
            or not values
            or not all(_identifier(value) for value in values)
            or len(set(values)) != len(values)
        ):
            raise ValueError(f"無効な状況変数または値域です: {key}")
    if math.prod(map(len, context.values())) > MAX_CONTEXTS:
        raise ValueError(f"状況の組合せが {MAX_CONTEXTS:,} 件を超えています")
    if not isinstance(model["rules"], list) or not isinstance(model["unmodeled"], list):
        raise ValueError("rules と unmodeled は配列で指定します")

    seen_ids, covered = set(), set()
    for rule in model["rules"]:
        _fields(rule, "id sources when unless action effect", "ルール")
        name = rule["id"]
        if not _identifier(name) or name in seen_ids:
            raise ValueError(f"無効または重複するルールIDです: {name}")
        seen_ids.add(name)
        _validate_sources(rule["sources"], lines, name)
        covered.update(rule["sources"])
        if not _identifier(rule["action"]) or rule["effect"] not in ("require", "forbid"):
            raise ValueError(f"{name}: action または effect が不正です")
        _validate_condition(rule["when"], context, name)
        if not isinstance(rule["unless"], list):
            raise ValueError(f"{name}: unless は配列で指定します")
        for exception in rule["unless"]:
            _validate_condition(exception, context, name)
    for gap in model["unmodeled"]:
        _fields(gap, "sources reason", "未変換項目")
        _validate_sources(gap["sources"], lines, "未変換項目")
        if not isinstance(gap["reason"], str) or not gap["reason"].strip():
            raise ValueError("未変換項目には reason が必要です")
        covered.update(gap["sources"])
    missing = lines.keys() - covered
    if missing:
        raise ValueError(f"原文に対応していない目印があります: {', '.join(sorted(missing))}")


def _holds(condition, state):
    return all(state[key] == value for key, value in condition.items())


def _overlap(requirement, prohibition, context):
    fixed = dict(requirement["when"])
    for key, value in prohibition["when"].items():
        if key in fixed and fixed[key] != value:
            return None
        fixed[key] = value
    exceptions = requirement["unless"] + prohibition["unless"]
    relevant = set(fixed)
    for exception in exceptions:
        relevant.update(exception)
    keys = sorted(relevant)
    domains = [(fixed[key],) if key in fixed else sorted(context[key]) for key in keys]
    for values in itertools.product(*domains):
        state = dict(zip(keys, values))
        if not any(_holds(exception, state) for exception in exceptions):
            return state
    return None


def check(prompt, model):
    """Find pairs for which both encoded rules govern the same binary action."""
    lines = source_lines(prompt)
    validate(model, lines)

    def with_text(refs):
        return [{"id": ref, "text": lines[ref]} for ref in refs]

    actions = {}
    for rule in sorted(model["rules"], key=lambda rule: rule["id"]):
        actions.setdefault(rule["action"], {"require": [], "forbid": []})[rule["effect"]].append(rule)

    conflicts = []
    for action, effects in sorted(actions.items()):
        for requirement, prohibition in itertools.product(effects["require"], effects["forbid"]):
            state = _overlap(requirement, prohibition, model["context"])
            if state is not None:
                conflicts.append({
                    "action": action,
                    "witness": state,
                    "required": {"rule": requirement["id"], "source": with_text(requirement["sources"])},
                    "forbidden": {"rule": prohibition["id"], "source": with_text(prohibition["sources"])},
                    "reason": "この状況では、同じ行動が必須であると同時に禁止されています。",
                })
    gaps = [{"source": with_text(gap["sources"]), "reason": gap["reason"]} for gap in model["unmodeled"]]
    status = "conflict" if conflicts else "incomplete" if gaps else "no_candidate"
    return {"status": status, "rule_count": len(model["rules"]), "conflicts": conflicts, "unmodeled": gaps}
