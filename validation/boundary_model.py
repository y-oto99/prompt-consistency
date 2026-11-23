"""Check permit decisions against safety properties over finite host metadata."""

from itertools import product

from checker.boundary import assess
from .boundary_cases import RELEASE, SUMMARY


def explore():
    origins = ("application", "user_interface", "retrieved_document", "tool_result",
               "image_text", "conversation_summary", None)
    releases = (RELEASE, {**RELEASE, "revision": 2})
    requests = (SUMMARY, *releases, None)
    proposals = (SUMMARY, *releases, {**SUMMARY, "audience": "public_portal"},
                 {**SUMMARY, "subject": "other_guide"})
    audiences = {"read_summary": "review_room", "release_revision": "public_portal"}
    total = permits = 0
    violation = None
    for origin, login, intent, proposal, classification, revision, approval, active in product(
        origins, (False, True), requests, proposals, ("restricted", "open", None),
        (1, 2), (*releases, None), (False, True),
    ):
        record = {
            "request_origin": origin, "authenticated_session": login,
            "intent": intent, "proposed": proposal, "resource_class": classification,
            "current_revision": revision, "approval": approval, "approval_active": active,
        }
        total += 1
        if assess(record)[0] != "allow":
            continue
        permits += 1
        missing_requirements = []
        if not login or origin not in {"application", "user_interface"}:
            missing_requirements.append("authenticated_authority")
        if intent != proposal or proposal["audience"] != audiences[proposal["operation"]]:
            missing_requirements.append("scope_binding")
        if classification is None:
            missing_requirements.append("classified_subject")
        if proposal["operation"] == "release_revision" and (
            classification != "open" or revision != proposal["revision"] or not active or approval != proposal
        ):
            missing_requirements.append("authorized_current_publication")
        if missing_requirements and violation is None:
            violation = {"properties": missing_requirements, "record": record}
    return {"combinations": total, "allowed": permits, "first_violation": violation}
