"""Replay a reported result independently of the agent's frontier logic."""

from .agents import SearchResult
from .environment import NetworkEnvironment
from .models import AttackState, GoalSpecification


def verify_result(
    environment: NetworkEnvironment, start: AttackState, goal: GoalSpecification,
    result: SearchResult,
) -> None:
    """Raise ValueError for an invalid route or inconsistent result shape."""
    environment.validate_query(start, goal)
    if not result.found:
        if result.states or result.actions or result.steps is not None or result.total_cost is not None:
            raise ValueError("An unreachable result must have no route or path metrics.")
        return

    if len(result.states) != len(result.actions) + 1 or result.steps != len(result.actions):
        raise ValueError("The number of states, actions and steps is inconsistent.")
    if result.states[0] != start:
        raise ValueError("The route does not begin at the requested state.")

    for index, (state, action, destination) in enumerate(
        zip(result.states, result.actions, result.states[1:]), start=1,
    ):
        if action.source != state or action.destination != destination:
            raise ValueError(f"Step {index} does not connect the reported states.")
        if action not in environment.successors(state):
            raise ValueError(f"Step {index} uses an illegal action {action.id!r}.")
    if not environment.goal_test(result.states[-1], goal):
        raise ValueError("The final state does not satisfy the requested goal.")
    if result.total_cost != sum(action.cost for action in result.actions):
        raise ValueError("Total effort does not equal the sum of the reported action costs.")
