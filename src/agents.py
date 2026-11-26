"""Original breadth-first and uniform-cost search over legal model transitions."""

from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import count
from time import perf_counter_ns

from .environment import NetworkEnvironment
from .models import AttackState, GoalSpecification, SearchAction


@dataclass(frozen=True)
class SearchResult:
    """A complete search outcome with nullable path metrics when unreachable."""

    algorithm: str
    found: bool
    states: tuple[AttackState, ...]
    actions: tuple[SearchAction, ...]
    steps: int | None
    total_cost: int | None
    expanded: int
    discovered: int
    elapsed_ns: int
    message: str

    @property
    def elapsed_ms(self) -> float:
        """Return search-only elapsed time in milliseconds."""
        return self.elapsed_ns / 1_000_000


class SearchAgent(ABC):
    """The common interface implemented by the two goal-based planners."""

    name: str

    def __init__(self, environment: NetworkEnvironment):
        self._environment = environment

    @abstractmethod
    def search(self, start: AttackState, goal: GoalSpecification) -> SearchResult:
        """Find a legal path under the agent's objective."""

    def _result(
        self,
        goal_state: AttackState | None,
        parents: dict[AttackState, SearchAction | None],
        expanded: int,
        started_ns: int,
    ) -> SearchResult:
        """Reconstruct the selected route inside the search timing boundary."""
        actions: list[SearchAction] = []
        states: list[AttackState] = []
        steps = total_cost = None
        message = "No modeled route satisfies the requested goal."
        if goal_state is not None:
            current = goal_state
            states.append(current)
            while (action := parents[current]) is not None:
                actions.append(action)
                current = action.source
                states.append(current)
            actions.reverse()
            states.reverse()
            steps = len(actions)
            total_cost = sum(action.cost for action in actions)
            message = "The starting state satisfies the goal." if steps == 0 else "Modeled goal reached."
        elapsed_ns = perf_counter_ns() - started_ns
        return SearchResult(
            self.name, goal_state is not None, tuple(states), tuple(actions), steps,
            total_cost, expanded, len(parents), elapsed_ns, message,
        )


class BFSAgent(SearchAgent):
    """Find a fewest-action route using a FIFO frontier."""

    name = "BFS"

    def search(self, start: AttackState, goal: GoalSpecification) -> SearchResult:
        """Expand states in discovery order, visiting each state at most once."""
        self._environment.validate_query(start, goal)
        started_ns = perf_counter_ns()
        frontier = deque([start])
        parents: dict[AttackState, SearchAction | None] = {start: None}
        expanded = 0
        while frontier:
            state = frontier.popleft()
            if self._environment.goal_test(state, goal):
                return self._result(state, parents, expanded, started_ns)
            expanded += 1
            for action in self._environment.successors(state):
                destination = action.destination
                if destination not in parents:
                    parents[destination] = action
                    frontier.append(destination)
        return self._result(None, parents, expanded, started_ns)


class UCSAgent(SearchAgent):
    """Find a least-effort route by settling states in increasing cost order."""

    name = "UCS"

    def search(self, start: AttackState, goal: GoalSpecification) -> SearchResult:
        """Replace a parent only for a strict improvement and ignore stale entries."""
        self._environment.validate_query(start, goal)
        started_ns = perf_counter_ns()
        sequence = count()
        frontier = [(0, next(sequence), start)]
        best = {start: 0}
        parents: dict[AttackState, SearchAction | None] = {start: None}
        expanded = 0
        while frontier:
            cost, _, state = heappop(frontier)
            if cost != best[state]:
                continue
            if self._environment.goal_test(state, goal):
                return self._result(state, parents, expanded, started_ns)
            expanded += 1
            for action in self._environment.successors(state):
                destination = action.destination
                candidate = cost + action.cost
                if destination not in best or candidate < best[destination]:
                    best[destination] = candidate
                    parents[destination] = action
                    heappush(frontier, (candidate, next(sequence), destination))
        return self._result(None, parents, expanded, started_ns)


def compare(
    environment: NetworkEnvironment, start: AttackState, goal: GoalSpecification,
) -> tuple[SearchResult, SearchResult]:
    """Run both agent implementations against the same model and query."""
    return BFSAgent(environment).search(start, goal), UCSAgent(environment).search(start, goal)
