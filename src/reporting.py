"""Human-readable route labels and portable JSON result exports."""

import json
from dataclasses import asdict
from pathlib import Path

from .agents import SearchResult
from .models import AttackState, GoalSpecification
from .remediation import Comparison, RemediationPreview

FAMILY_LABELS = {
    "vulnerable_service": "Vulnerable-service access",
    "local_escalation": "Local privilege escalation",
    "credential_login": "Credential-based login",
}
FIX_LABELS = {
    "disable_weakness": "Disable weakness",
    "revoke_credential": "Revoke credential access",
    "revoke_permission": "Revoke permission",
    "block_connection": "Block directed connection",
}


def state_label(state: AttackState) -> str:
    """Label both components of one search state."""
    return f"{state.asset_id}/{state.privilege_level}"


def route_label(result: SearchResult, arrow: str = " → ") -> str:
    """Format an ordered route, including an explicit unreachable result."""
    if not result.found:
        return "No modeled route"
    return arrow.join(state_label(state) for state in result.states)


def export_comparison(
    destination: Path, scenario_id: str, start: AttackState, goal: GoalSpecification,
    results: Comparison, preview: RemediationPreview | None,
) -> None:
    """Write query, route and optional preview results in a local JSON file."""
    report = {
        "scenario_id": scenario_id,
        "start": asdict(start),
        "goal": asdict(goal),
        "comparison": [asdict(result) for result in results],
        "remediation": None if preview is None else asdict(preview),
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
