"""Check trusted provenance metadata against a narrow authority policy."""

_ALLOWED = {
    "app_policy": {"select_display_label", "summarize_reference"},
    "user_request": {"summarize_reference"},
    "reference_data": set(),
}


def check_authority(record):
    if set(record) != {"source", "kind", "action"}:
        raise ValueError("source / kind / action が必要です")
    source, kind, action = (record[key] for key in ("source", "kind", "action"))
    if source not in _ALLOWED or kind not in {"instruction", "quotation"}:
        raise ValueError("元の分類に含まれない出所または種類です")
    if not isinstance(action, str) or action not in _ALLOWED["app_policy"]:
        raise ValueError("未定義の行動です")
    if kind == "quotation":
        return "quoted_content"
    if action in _ALLOWED[source]:
        return "authorized"
    return "unauthorized_instruction"
