# Viva preparation

Use your actual project contributions and their evidence when preparing for the individual viva. The proposal allocation is a planning record. This guide explains the implementation and provides a route you can trace by hand.

## Problem and formulation

An assumed state is a synthetic asset and the privilege held there. A goal specifies a target asset and the minimum privilege. The environment admits an action only when the declared rule matches the state and all its conditions hold. Two routes can reach the same target with different step counts and cumulative effort.

| PEAS component | In this project |
| --- | --- |
| Performance | Legal goal route, the agent's own objective, expansions and search time, and correct reporting of fix impact |
| Environment | Finite synthetic assets, privileges, links and declared conditions |
| Actuators | Generate allowed transitions, present an explanation and rerun a model preview |
| Sensors | Validated scenario, selected starting state, goal and optional fix |

The search is fully observable within the model, deterministic, static per run and discrete. One goal-based agent runs at a time. UCS chooses among goal paths by cumulative modeled effort.

## Trace the cost trade-off

Open [the fixture](../data/scenarios/checked/cost_tradeoff.json) and [the hand-derived expectations](../data/checked-expectations.json).

1. Mark the initial state and write down the action IDs allowed by the environment in ascending ID order.
2. For BFS, put the start in a FIFO queue. At each pop, check the goal, expand if needed, and mark newly enqueued states with their incoming action. Follow the first-found goal's parent pointers to the start.
3. For UCS, attach cumulative costs to frontier entries. Pop the least cost, retain only a strictly better cost for each state, and skip entries whose cost exceeds the saved best cost. Follow parent pointers when a current goal is popped.
4. Independently total each route's actions and effort. Explain how a direct costly move can win on steps while a sequence of cheaper moves wins on effort.
5. Compare computed paths against the fixture expectations. Then run the console and inspect each transition's explanation.

Start at `entry/user`. The first expansion admits `a_direct` to `archive/user` at effort 5 and `b_relay` to `relay/user` at effort 1. BFS places the archive first and returns after one expansion. UCS pops the relay at cost 1, then `c_forward` improves the archive's cost to 2. The archive now leaves the heap before its older, cost-5 entry. UCS returns two actions after two expansions.

```bash
python -m src.cli --scenario data/scenarios/checked/cost_tradeoff.json
python -m src.cli --scenario data/scenarios/checked/alternate_route.json --list-fixes
```

## Questions to practice

| Question | Answer to work through |
| --- | --- |
| Why is there no route history in a state? | The legality of every action depends only on the current asset, its privilege and immutable rules. A credential capability comes from the current asset and disappears from consideration when the state moves elsewhere. |
| How does the goal handle a stronger privilege? | `goal_test` compares the asset and compares privilege ranks in the declared order. A state on the target at `admin` meets a `user` goal. |
| What conditions make a remote action legal? | The action declares its directed connection and destination service. Their records must be enabled. The privilege and any permission conditions must hold. The exact family also requires its declared weakness or authorized credential capability. |
| Why does BFS minimize actions? | The queue processes depth layers in order. A state's initial discovery is at its least possible depth and supplies the parent used for the route. |
| Why does UCS minimize effort? | It considers states by cumulative effort. With positive costs, any cheaper goal route would have a prefix queued or popped earlier. A goal is accepted when popped with the current best cost. |
| Why keep stale heap entries? | A new cheaper entry can be pushed without editing an existing heap item. Comparing a popped cost against the saved best cost prevents a superseded entry from being expanded. |
| What happens on equal-cost alternatives? | The successors appear in action-ID order and the heap follows insertion order for equal priorities. Equal candidates keep the existing parent. |
| What counts as an expansion? | A current frontier state that fails the goal test triggers a successor call and counts once. A returned goal and a stale entry trigger no successor call. |
| How is a no-solution result represented? | The frontier is exhausted. Reachability is false and path step and cost metrics are absent. A start already meeting the goal is a valid route of zero actions and zero effort. |
| How can a fixed model still reach the goal? | A fix disables one declarative record. Searches may find a different sequence that depends on other enabled records. Explain this using the alternate-route fixture. |
| What was timed and how often? | Only each search interval. The standard run uses 20 generated models and 10 trials per algorithm for 400 observations. Trials on one model measure timing variability and share the same logical input. |
| What did the generated cases show? | Both agents reached 15 targets. UCS used lower effort and BFS used fewer steps on six of those 15 cases. Use case-01 to connect this pattern to its individual route and timing records. |
| Which OOP features are present? | The environment owns private indices, immutable state records are value objects, `SearchAgent` supplies an abstract method and each concrete agent overrides it. Callers can run either through the same contract. |

## Code and results to open

- `src/models.py` for `AttackState`, `Scenario` and the query types.
- `src/environment.py` for `successors`, `goal_test` and `apply_fix`.
- `src/agents.py` for discovery, relaxation, parent pointers and counters.
- `src/verification.py` for independent path replay.
- `src/remediation.py` for before/after comparison.
- `outputs/results/search_summary.csv` and the [report](report.md) for measured comparisons and cautious interpretation.

Keep the distinction between model and real configuration clear. Effort values represent assigned teaching units. Saying that a fix removes every modeled route is a claim about the selected scenario and query.
