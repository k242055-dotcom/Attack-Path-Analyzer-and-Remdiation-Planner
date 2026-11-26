"""Check generated scenario reproducibility and intended search variation."""

import random
from collections import Counter

import pytest

from src.agents import BFSAgent, UCSAgent
from src.environment import NetworkEnvironment
from src.scenario_generator import canonical_json, generate_scenarios, generate_to_directory
from src.validation import load_scenario, parse_scenario


def test_seed_reproduces_canonical_json_independently_of_global_randomness():
    first = [canonical_json(item) for item in generate_scenarios()]
    state = random.getstate()
    try:
        random.seed(87)
        random.random()
        second = [canonical_json(item) for item in generate_scenarios(seed=42)]
    finally:
        random.setstate(state)
    assert len(first) == 20
    assert first == second
    assert first != [canonical_json(item) for item in generate_scenarios(seed=43)]


def test_generated_json_round_trips_with_unique_models(tmp_path):
    paths = generate_to_directory(output_dir=tmp_path)
    assert [path.name for path in paths] == [f"case-{case:02d}.json" for case in range(1, 21)]
    scenarios = [load_scenario(path) for path in paths]
    assert len({scenario.id for scenario in scenarios}) == 20
    assert len({len(scenario.assets) for scenario in scenarios}) > 5
    for path, scenario in zip(paths, scenarios, strict=True):
        assert 10 <= len(scenario.assets) <= 30
        assert scenario.metadata["seed"] == 42
        entities = (
            scenario.assets + scenario.services + scenario.connections + scenario.weaknesses
            + scenario.permissions + scenario.credentials + scenario.actions
        )
        assert len(entities) == len({entity.id for entity in entities})
        assert b"\r\n" not in path.read_bytes()


def test_templates_give_intended_search_outcomes_and_all_three_action_families():
    patterns = Counter()
    families = set()
    for document in generate_scenarios():
        scenario = parse_scenario(document)
        pattern = scenario.metadata["pattern"]
        patterns[pattern] += 1
        environment = NetworkEnvironment(scenario)
        bfs = BFSAgent(environment).search(scenario.start, scenario.goal)
        ucs = UCSAgent(environment).search(scenario.start, scenario.goal)
        assert bfs.found == ucs.found == (pattern != "unreachable")
        families.update(action.family for result in (bfs, ucs) for action in result.actions)
        if pattern == "trade-off":
            assert (bfs.steps, bfs.total_cost) == (1, 5)
            assert (ucs.steps, ucs.total_cost) == (3, 3)
        if pattern == "cyclic":
            assert any(action.family == "local_escalation" for action in ucs.actions)
    assert patterns == {"trade-off": 5, "branching": 5, "unreachable": 5, "cyclic": 5}
    assert families == {"vulnerable_service", "credential_login", "local_escalation"}


@pytest.mark.parametrize("seed,cases", [(True, 1), (2**63, 1), (42, 0), (42, 100)])
def test_invalid_generation_parameters(seed, cases):
    with pytest.raises(ValueError):
        generate_scenarios(seed, cases)
