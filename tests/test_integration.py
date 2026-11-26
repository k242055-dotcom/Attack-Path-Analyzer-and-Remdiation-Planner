"""Exercise root-level entrypoints and their public outputs."""

import json
import subprocess
import sys

from streamlit.testing.v1 import AppTest

from src.paths import PROJECT_ROOT


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Execute the documented console command from the project root."""
    return subprocess.run(
        [sys.executable, "-m", "src.cli", *args],
        cwd=PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8", timeout=20,
    )


def test_console_search_and_fix_export(tmp_path):
    destination = tmp_path / "result" / "preview.json"
    result = run_cli(
        "--scenario", "data/scenarios/checked/alternate_route.json",
        "--fix", "disable_weakness:weak_a_direct", "--json-out", str(destination),
    )
    assert result.returncode == 0, result.stderr
    assert "BFS" in result.stdout and "UCS" in result.stdout
    assert "replacement route" in result.stdout
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["scenario_id"] == "alternate_route"
    assert [item["total_cost"] for item in payload["comparison"]] == [2, 2]
    assert [item["total_cost"] for item in payload["remediation"]["after"]] == [4, 4]
    assert payload["remediation"]["fix"]["record_id"] == "weak_a_direct"


def test_console_lists_cases_and_enabled_fixes():
    cases = run_cli("--list-scenarios")
    assert cases.returncode == 0
    assert "data/scenarios/checked/simple_path.json" in cases.stdout
    fixes = run_cli("--list-fixes")
    assert fixes.returncode == 0
    assert "revoke_credential:cap_relay_archive" in fixes.stdout


def test_console_unreachable_and_invalid_input(tmp_path):
    unreachable = run_cli("--scenario", "data/scenarios/checked/unreachable_goal.json")
    assert unreachable.returncode == 0
    assert "No modeled route" in unreachable.stdout
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    invalid = run_cli("--scenario", str(bad))
    assert invalid.returncode == 2
    assert "Malformed JSON" in invalid.stderr
    assert "Traceback" not in invalid.stderr
    invalid_start = run_cli("--start-asset", "")
    assert invalid_start.returncode == 2
    assert "unknown asset" in invalid_start.stderr


def test_dashboard_compare_preview_and_discard():
    dashboard = AppTest.from_file(PROJECT_ROOT / "src" / "main.py", default_timeout=25).run()
    assert not dashboard.exception
    assert [tab.label for tab in dashboard.tabs] == ["Network", "Compare", "Remediation", "Experiments", "Help"]
    dashboard.button(key="compare_agents").click().run()
    assert not dashboard.exception
    assert [metric.value for metric in dashboard.metric if metric.label == "Effort"] == ["5", "5"]
    dashboard.button(key="preview_fix").click().run()
    assert not dashboard.exception
    assert sum("removes every modeled route" in item.value for item in dashboard.info) == 2
    dashboard.button(key="discard_fix").click().run()
    assert not dashboard.exception
    assert all("removes every modeled route" not in item.value for item in dashboard.info)
