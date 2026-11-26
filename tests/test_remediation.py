"""Check preview outcomes, changed records and baseline immutability."""

import json
from dataclasses import replace

import pytest

from src.agents import compare
from src.environment import NetworkEnvironment
from src.models import Remediation
from src.paths import CHECKED_DIR, DATA_DIR
from src.remediation import preview_fix
from src.validation import ValidationError, load_scenario

EXPECTATIONS = json.loads((DATA_DIR / "checked-expectations.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case_id", ["blocking_fix", "alternate_route"])
def test_preview_matches_hand_computation_and_preserves_baseline(case_id):
    scenario = load_scenario(CHECKED_DIR / f"{case_id}.json")
    environment = NetworkEnvironment(scenario)
    expected = EXPECTATIONS[case_id]["fix"]
    fix = Remediation(expected["kind"], expected["record_id"])
    preview = preview_fix(environment, scenario.start, scenario.goal, fix)
    assert preview.fix == fix
    assert preview.record_changed
    assert preview.removed_transitions > 0
    assert environment.scenario is scenario
    assert fix in environment.fixes()
    assert fix not in environment.apply_fix(fix).fixes()

    unchanged = compare(environment, scenario.start, scenario.goal)
    for before, after, fresh in zip(preview.before, preview.after, unchanged):
        solution = expected[after.algorithm]
        assert after.found == (solution["steps"] is not None)
        assert (after.steps, after.total_cost) == (solution["steps"], solution["effort"])
        assert [action.id for action in after.actions] == solution["action_ids"]
        assert replace(before, elapsed_ns=0) == replace(fresh, elapsed_ns=0)
    effect = "replacement route" if case_id == "alternate_route" else "removes every"
    assert all(effect in message for message in preview.effects)


@pytest.mark.parametrize(("case_id", "kind", "record_id"), [
    ("simple_path", "revoke_credential", "cap_relay_archive"),
    ("blocking_fix", "revoke_permission", "permission_archive"),
])
def test_access_revocation_blocks_required_route(case_id, kind, record_id):
    scenario = load_scenario(CHECKED_DIR / f"{case_id}.json")
    preview = preview_fix(NetworkEnvironment(scenario), scenario.start, scenario.goal, Remediation(kind, record_id))
    assert all(result.found for result in preview.before)
    assert all(not result.found for result in preview.after)
    assert preview.removed_transitions == 2


def test_fix_with_no_modeled_effect_and_already_disabled_record():
    scenario = load_scenario(CHECKED_DIR / "unreachable_goal.json")
    environment = NetworkEnvironment(scenario)
    ineffective = Remediation("disable_weakness", "weak_cross_blocked_link")
    already_disabled = Remediation("block_connection", "link_relay_archive")
    first = preview_fix(environment, scenario.start, scenario.goal, ineffective)
    second = preview_fix(environment, scenario.start, scenario.goal, already_disabled)
    assert first.record_changed and not second.record_changed
    assert first.removed_transitions == second.removed_transitions == 0
    assert all("remains unreachable" in effect for effect in first.effects)


def test_unknown_fix_reports_exact_record():
    scenario = load_scenario(CHECKED_DIR / "simple_path.json")
    with pytest.raises(ValidationError, match="unknown record 'missing'"):
        preview_fix(NetworkEnvironment(scenario), scenario.start, scenario.goal, Remediation("block_connection", "missing"))
