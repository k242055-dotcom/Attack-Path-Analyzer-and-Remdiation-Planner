"""Compare one change against the immutable baseline scenario."""

from dataclasses import dataclass

from .agents import SearchResult, compare
from .environment import NetworkEnvironment
from .models import AttackState, GoalSpecification, Remediation
from .verification import verify_result

Comparison = tuple[SearchResult, SearchResult]


@dataclass(frozen=True)
class RemediationPreview:
    """The exact change and its effect on each selected result."""

    fix: Remediation
    record_changed: bool
    removed_transitions: int
    before: Comparison
    after: Comparison
    effects: tuple[str, str]


def _effect(before: SearchResult, after: SearchResult) -> str:
    if not before.found:
        return "The goal remains unreachable in this model."
    if not after.found:
        return "The fix removes every modeled route to this goal."
    if before.actions != after.actions:
        return "The goal remains reachable via a replacement route."
    return "The goal remains reachable via the same selected route."


def preview_fix(
    environment: NetworkEnvironment, start: AttackState, goal: GoalSpecification, fix: Remediation,
) -> RemediationPreview:
    """Rerun both agents on a derived environment and replay their routes."""
    updated = environment.apply_fix(fix)
    before = compare(environment, start, goal)
    after = compare(updated, start, goal)
    for base_result, new_result in zip(before, after):
        verify_result(environment, start, goal, base_result)
        verify_result(updated, start, goal, new_result)

    removed_transitions = 0
    for asset in environment.asset_ids:
        for privilege in environment.scenario.privilege_levels:
            state = AttackState(asset, privilege)
            removed_transitions += len(environment.successors(state)) - len(updated.successors(state))
    return RemediationPreview(
        fix, fix in environment.fixes(), removed_transitions, before, after,
        (_effect(before[0], after[0]), _effect(before[1], after[1])),
    )
