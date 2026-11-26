"""Exercise each legal transition and the conditions that exclude it."""

import pytest

from src.environment import NetworkEnvironment
from src.models import AttackState, GoalSpecification
from src.validation import parse_scenario


def test_states_are_stable_value_objects():
    state = AttackState("b", "user")
    assert state.key() == ("b", "user")
    assert {state, AttackState("b", "user"), AttackState("b", "admin")} == {
        state, AttackState("b", "admin"),
    }
    assert state < AttackState("c", "guest")


def test_all_three_transition_families_have_exact_sources_grants_and_costs(model_data):
    scenario = parse_scenario(model_data)
    environment = NetworkEnvironment(scenario)
    (entry,) = environment.successors(scenario.start)
    (local,) = environment.successors(entry.destination)
    (login,) = environment.successors(local.destination)

    assert (entry.family, entry.source, entry.destination, entry.cost) == (
        "vulnerable_service", AttackState("a", "user"), AttackState("b", "user"), 2,
    )
    assert (local.family, local.source, local.destination, local.cost) == (
        "local_escalation", AttackState("b", "user"), AttackState("b", "admin"), 3,
    )
    assert (login.family, login.source, login.destination, login.cost) == (
        "credential_login", AttackState("b", "admin"), AttackState("c", "admin"), 1,
    )
    assert dict(entry.entity_ids) == {
        "connection_id": "link-a-b", "service_id": "service-b",
        "weakness_id": "condition-remote", "permission_id": "allow-a-b",
    }
    assert "condition-local" in str(local.preconditions)
    assert "explicitly authorized for login service service-c" in str(login.preconditions)
    assert (entry.min_privilege, local.min_privilege, login.min_privilege) == ("user", "user", "admin")
    assert environment.goal_test(login.destination, scenario.goal)
    assert environment.goal_test(login.destination, GoalSpecification("c", "guest"))
    assert not environment.goal_test(AttackState("c", "user"), scenario.goal)
    assert not environment.goal_test(AttackState("b", "admin"), scenario.goal)


@pytest.mark.parametrize(
    ("collection", "index", "state"),
    [
        ("connections", 0, AttackState("a", "user")),
        ("connections", 1, AttackState("b", "admin")),
        ("services", 0, AttackState("a", "user")),
        ("services", 1, AttackState("b", "admin")),
        ("weaknesses", 0, AttackState("a", "user")),
        ("weaknesses", 1, AttackState("b", "user")),
        ("credentials", 0, AttackState("b", "admin")),
        ("permissions", 0, AttackState("a", "user")),
        ("permissions", 1, AttackState("b", "user")),
        ("permissions", 2, AttackState("b", "admin")),
    ],
)
def test_disabling_any_required_record_excludes_its_transition(model_data, collection, index, state):
    model_data[collection][index]["enabled"] = False
    environment = NetworkEnvironment(parse_scenario(model_data))
    assert environment.successors(state) == ()


def test_preconditions_apply_to_actual_current_privilege_and_location(model_data):
    environment = NetworkEnvironment(parse_scenario(model_data))
    assert environment.successors(AttackState("a", "guest")) == ()
    assert environment.successors(AttackState("b", "guest")) == ()
    assert [action.id for action in environment.successors(AttackState("b", "user"))] == ["rule-b-local"]
    assert [action.id for action in environment.successors(AttackState("b", "admin"))] == ["rule-b-c"]
    assert environment.successors(AttackState("c", "admin")) == ()
    assert environment.successors(AttackState("d", "admin")) == ()


def test_declared_topology_and_services_do_not_imply_routes(model_data):
    model_data["actions"] = []
    environment = NetworkEnvironment(parse_scenario(model_data))
    for asset_id in environment.asset_ids:
        assert environment.successors(AttackState(asset_id, "admin")) == ()


def test_cross_asset_grant_is_exact_and_reverse_connectivity_is_absent(model_data):
    environment = NetworkEnvironment(parse_scenario(model_data))
    (entry,) = environment.successors(AttackState("a", "admin"))
    assert entry.destination == AttackState("b", "user")
    assert all(action.destination.asset_id != "a" for action in environment.successors(entry.destination))


def test_successors_use_lexical_rule_ids_independent_of_json_order(model_data):
    model_data["actions"].append({**model_data["actions"][0], "id": "a-earlier-rule", "cost": 5})
    first = NetworkEnvironment(parse_scenario(model_data))
    model_data["actions"].reverse()
    second = NetworkEnvironment(parse_scenario(model_data))
    assert first.successors(first.scenario.start) == second.successors(second.scenario.start)
    assert [action.id for action in first.successors(first.scenario.start)] == ["a-earlier-rule", "rule-a-b"]
    assert [action.cost for action in first.successors(first.scenario.start)] == [5, 2]
