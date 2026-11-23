"""Pure authorization policy for proposed actions in a synthetic application."""

from dataclasses import dataclass

# These values represent bindings supplied by the application, not claims in text.
ACTIONS = {"read_summary": {"review_room"}, "release_revision": {"public_portal"}}
REQUEST_ORIGINS = {"user_interface", "application"}
REFERENCE_ORIGINS = {"retrieved_document", "tool_result", "image_text", "conversation_summary"}
SENSITIVITY = {"open", "restricted"}


@dataclass(frozen=True)
class Action:
    operation: str
    subject: str
    revision: int
    audience: str


def parse_action(value):
    if type(value) is not dict or set(value) != {"operation", "subject", "revision", "audience"}:
        raise ValueError("invalid action schema")
    action = Action(**value)
    if not all(type(x) is str and x for x in (action.operation, action.subject, action.audience)):
        raise ValueError("non-empty operation, subject, and audience expected")
    if type(action.revision) is not int or action.revision < 1:
        raise ValueError("positive integer revision expected")
    return action


def assess(record, strategy="bound_effect"):
    """Return a decision and a reason without calling or executing any tool."""
    if strategy not in {"channel_only", "operation_only", "bound_effect"}:
        raise ValueError("unknown strategy")
    origin = record["request_origin"]
    if record["authenticated_session"] is not True:
        return "deny", "session_not_authenticated"
    if origin in REFERENCE_ORIGINS:
        return "deny", "reference_has_no_authority"
    if origin not in REQUEST_ORIGINS:
        return "review", "missing_request_provenance"
    if strategy == "channel_only":
        return "allow", "trusted_channel"
    try:
        proposed = parse_action(record["proposed"])
    except ValueError:
        return "deny", "invalid_proposal_schema"
    if proposed.operation not in ACTIONS:
        return "deny", "unknown_operation"
    if strategy == "operation_only":
        return "allow", "permitted_operation_name"
    if record["intent"] is None:
        return "review", "missing_confirmed_intent"
    intent = parse_action(record["intent"])
    if proposed != intent:
        return "deny", "proposal_differs_from_confirmed_intent"
    if proposed.audience not in ACTIONS[proposed.operation]:
        return "deny", "disallowed_audience"
    classification = record["resource_class"]
    if classification not in SENSITIVITY:
        return "review", "unclassified_resource"
    if proposed.operation == "read_summary":
        return "allow", "scoped_read"
    if proposed.revision != record["current_revision"]:
        return "deny", "stale_revision"
    if classification == "restricted":
        return "deny", "restricted_resource_cannot_be_released"
    approval = record["approval"]
    if approval is None or record["approval_active"] is not True:
        return "deny", "no_active_approval"
    if parse_action(approval) != proposed:
        return "deny", "approval_bound_to_different_effect"
    return "allow", "approved_exact_revision_and_audience"
