"""Small manually derived cases exercise the agents independently."""

from dataclasses import replace

import pytest

from src.agents import BFSAgent, SearchAgent, UCSAgent, compare
from src.environment import NetworkEnvironment
from src.models import AttackState, GoalSpecification
from src.validation import ValidationError, parse_scenario
from src.verification import verify_result


@pytest.fixture
def graph():
    """Return a two-route graph with a cycle and an isolated target."""
    raw = {
        "schema_version": 1,
        "id": "agent_spec",
        "name": "Agent specification",
        "description": "A direct rule costs five, a two-step path costs two, and a return edge forms a cycle.",
        "privilege_levels": ["guest", "user", "admin"],
        "assets": [{"id": name, "label": name.capitalize()} for name in ("entry", "relay", "archive", "isolated")],
        "services": [],
        "connections": [],
        "weaknesses": [],
        "credentials": [],
        "permissions": [],
        "actions": [],
        "start": {"asset_id": "entry", "privilege_level": "user"},
        "goal": {"asset_id": "archive", "required_privilege": "user"},
    }
    for name in ("entry", "relay", "archive"):
        raw["services"].append({
            "id": f"svc_{name}", "asset_id": name, "label": "Model service", "enabled": True, "login": False,
        })
        raw["weaknesses"].append({
            "id": f"weak_{name}", "asset_id": name, "service_id": f"svc_{name}",
            "granted_privilege": "user", "enabled": True,
        })
    for action_id, source, target, effort in (
        ("a_direct", "entry", "archive", 5),
        ("b_relay", "entry", "relay", 1),
        ("c_forward", "relay", "archive", 1),
        ("d_return", "relay", "entry", 1),
    ):
        raw["connections"].append({
            "id": f"link_{action_id}", "source_asset_id": source, "destination_asset_id": target, "enabled": True,
        })
        raw["actions"].append({
            "id": action_id, "family": "vulnerable_service", "source_asset_id": source,
            "min_privilege": "user", "cost": effort, "connection_id": f"link_{action_id}",
            "service_id": f"svc_{target}", "weakness_id": f"weak_{target}",
        })
    return raw


def test_bfs_and_ucs_optimize_different_objectives(graph):
    env = NetworkEnvironment(parse_scenario(graph))
    start, goal = env.scenario.start, env.scenario.goal
    bfs, ucs = compare(env, start, goal)
    assert (bfs.steps, bfs.total_cost, bfs.expanded, bfs.discovered) == (1, 5, 1, 3)
    assert [action.id for action in bfs.actions] == ["a_direct"]
    assert (ucs.steps, ucs.total_cost, ucs.expanded, ucs.discovered) == (2, 2, 2, 3)
    assert [action.id for action in ucs.actions] == ["b_relay", "c_forward"]
    assert bfs.steps < ucs.steps and ucs.total_cost <= bfs.total_cost
    for result in (bfs, ucs):
        verify_result(env, start, goal, result)


def test_ucs_settles_ties_in_discovery_order_and_is_deterministic(graph):
    graph["actions"][0]["cost"] = 2
    graph["actions"].reverse()
    env = NetworkEnvironment(parse_scenario(graph))
    first, second = (UCSAgent(env).search(env.scenario.start, env.scenario.goal) for _ in range(2))
    assert [action.id for action in first.actions] == ["a_direct"]
    assert first.total_cost == 2
    assert replace(first, elapsed_ns=0) == replace(second, elapsed_ns=0)


def test_bfs_tie_uses_rule_id_even_when_equal_step_route_costs_less(graph):
    graph["actions"].append(dict(graph["actions"][0], id="a_second", cost=3))
    graph["actions"].reverse()
    env = NetworkEnvironment(parse_scenario(graph))
    result = BFSAgent(env).search(env.scenario.start, env.scenario.goal)
    assert [action.id for action in result.actions] == ["a_direct"]
    assert result.total_cost == 5


@pytest.mark.parametrize("agent_class", [BFSAgent, UCSAgent])
def test_unreachable_privilege_and_cycle_with_stale_ucs_entry(graph, agent_class):
    env = NetworkEnvironment(parse_scenario(graph))
    goal = GoalSpecification("archive", "admin")
    result = agent_class(env).search(env.scenario.start, goal)
    assert not result.found
    assert result.states == result.actions == ()
    assert result.steps is result.total_cost is None
    assert (result.expanded, result.discovered) == (3, 3)
    verify_result(env, env.scenario.start, goal, result)


@pytest.mark.parametrize("agent_class", [BFSAgent, UCSAgent])
def test_start_already_meets_lower_privilege_goal(graph, agent_class):
    env = NetworkEnvironment(parse_scenario(graph))
    start = AttackState("entry", "admin")
    goal = GoalSpecification("entry", "guest")
    agent = agent_class(env)
    assert isinstance(agent, SearchAgent)
    result = agent.search(start, goal)
    assert result.found
    assert result.states == (start,)
    assert result.actions == ()
    assert (result.steps, result.total_cost, result.expanded, result.discovered) == (0, 0, 0, 1)
    assert result.elapsed_ns >= 0
    verify_result(env, start, goal, result)


def test_invalid_query_has_a_validation_error(graph):
    env = NetworkEnvironment(parse_scenario(graph))
    with pytest.raises(ValidationError, match="asset"):
        BFSAgent(env).search(AttackState("unknown", "user"), env.scenario.goal)


def test_path_replay_detects_mismatched_cost_endpoints_and_actions(graph):
    env = NetworkEnvironment(parse_scenario(graph))
    start, goal = env.scenario.start, env.scenario.goal
    result = BFSAgent(env).search(start, goal)
    falsified_action = replace(result.actions[0], id="imagined_rule")
    for inconsistent in (
        replace(result, total_cost=0),
        replace(result, steps=2),
        replace(result, states=tuple(reversed(result.states))),
        replace(result, actions=(falsified_action,)),
    ):
        with pytest.raises(ValueError):
            verify_result(env, start, goal, inconsistent)
    with pytest.raises(ValueError, match="goal"):
        verify_result(env, start, GoalSpecification("isolated", "guest"), result)
