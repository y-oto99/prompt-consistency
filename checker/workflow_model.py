"""Explicit-state model checking for a synthetic asynchronous review workflow."""

from collections import defaultdict, deque
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Publication:
    revision: int
    approved: int
    approval_active: bool
    queued: int


@dataclass(frozen=True)
class State:
    revision: int = 1
    under_review: int = 0
    approved: int = 0
    approval_active: bool = False
    queued: int = 0
    publication: Publication | None = None


@dataclass(frozen=True)
class Protocol:
    bind_revision: bool
    check_active_at_publish: bool
    clear_stale_queue: bool


PROTOCOLS = {
    "queue_check_only": Protocol(False, False, False),
    "bind_revision": Protocol(True, False, True),
    "guarded": Protocol(True, True, True),
    "guarded_without_recovery": Protocol(True, True, False),
}


def transitions(s, p, max_revision):
    if s.publication:
        return
    if s.revision < max_revision:
        yield "edit_new_revision", replace(s, revision=s.revision + 1)
    if not s.under_review:
        yield "request_review_current", replace(s, under_review=s.revision)
    if s.under_review:
        yield "approve_reviewed_revision", replace(
            s, approved=s.under_review, approval_active=True, under_review=0
        )
        yield "cancel_review", replace(s, under_review=0)
    if s.approval_active:
        yield "revoke_approval", replace(s, approval_active=False)
    if not s.queued and s.approval_active and s.approved == s.revision:
        yield "queue_current_revision", replace(s, queued=s.revision)
    if s.queued:
        same_revision = s.queued == s.revision == s.approved
        if (
            (not p.bind_revision or same_revision)
            and (not p.check_active_at_publish or s.approval_active)
        ):
            published = Publication(s.revision, s.approved, s.approval_active, s.queued)
            yield "publish", replace(s, publication=published)
        if p.clear_stale_queue and (not same_revision or not s.approval_active):
            yield "clear_stale_or_revoked_queue", replace(s, queued=0)


# Properties are evaluated on the recorded publication independently of queue guards.
PROPERTIES = {
    "published_approved_revision": lambda s: not s.publication or s.publication.revision == s.publication.approved,
    "publication_has_active_approval": lambda s: not s.publication or s.publication.approval_active,
    "published_queued_revision": lambda s: not s.publication or s.publication.revision == s.publication.queued,
}


def model_check(protocol, max_revision=2):
    if not 1 <= max_revision <= 4:
        raise ValueError("model bound must be 1–4 revisions")
    initial = State()
    predecessors = {initial: None}
    incoming = defaultdict(set)
    frontier = deque([initial])
    failures = {}
    reached_publications = []
    edges = 0

    def trace(state):
        events = []
        while predecessors[state] is not None:
            state, event = predecessors[state]
            events.append(event)
        return list(reversed(events))

    while frontier:
        state = frontier.popleft()
        if state.publication:
            reached_publications.append(state)
        for name, holds in PROPERTIES.items():
            if name not in failures and not holds(state):
                failures[name] = trace(state)
        for event, target in transitions(state, protocol, max_revision):
            incoming[target].add(state)
            edges += 1
            if target not in predecessors:
                predecessors[target] = (state, event)
                frontier.append(target)

    # Reverse reachability checks AG EF Published (a possible continuation from
    # every reachable state). It does not assert eventual publication on all paths.
    can_complete = set(reached_publications)
    frontier.extend(reached_publications)
    while frontier:
        for previous in incoming[frontier.popleft()]:
            if previous not in can_complete:
                can_complete.add(previous)
                frontier.append(previous)
    stranded = next((state for state in predecessors if state not in can_complete), None)
    return {
        "bound": max_revision,
        "reachable_states": len(predecessors),
        "transitions": edges,
        "properties": {name: {"holds": name not in failures, "counterexample": failures.get(name)}
                       for name in PROPERTIES},
        "completion_possible_from_all_states": stranded is None,
        "stranded_trace": trace(stranded) if stranded is not None else None,
        "stranded_state": repr(stranded) if stranded is not None else None,
        "published_example": trace(reached_publications[0]) if reached_publications else None,
    }
