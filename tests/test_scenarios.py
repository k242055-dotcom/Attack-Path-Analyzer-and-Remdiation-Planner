"""Verify all bundled hand-checked cases against independently derived routes."""

import json

import pytest

from src.agents import compare
from src.environment import NetworkEnvironment
from src.paths import CHECKED_DIR, DATA_DIR
from src.validation import load_scenario
from src.verification import verify_result

EXPECTATIONS = json.loads((DATA_DIR / "checked-expectations.json").read_text(encoding="utf-8"))


def test_manifest_covers_the_six_checked_cases():
    assert set(EXPECTATIONS) == {path.stem for path in CHECKED_DIR.glob("*.json")}
    assert len(EXPECTATIONS) == 6


@pytest.mark.parametrize("case_id", EXPECTATIONS)
def test_checked_case_matches_hand_computation(case_id):
    scenario = load_scenario(CHECKED_DIR / f"{case_id}.json")
    environment = NetworkEnvironment(scenario)
    bfs, ucs = compare(environment, scenario.start, scenario.goal)
    for result in (bfs, ucs):
        expected = EXPECTATIONS[case_id][result.algorithm]
        assert result.found == (expected["steps"] is not None)
        assert result.steps == expected["steps"]
        assert result.total_cost == expected["effort"]
        assert [action.id for action in result.actions] == expected["action_ids"]
        verify_result(environment, scenario.start, scenario.goal, result)
    if bfs.found:
        assert bfs.total_cost >= ucs.total_cost
        assert bfs.steps <= ucs.steps
