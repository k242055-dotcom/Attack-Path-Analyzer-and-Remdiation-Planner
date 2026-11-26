"""Generate reproducible synthetic scenarios with explicit transition rules."""

import argparse
import json
import random
from pathlib import Path
from typing import Any

from .models import PRIVILEGE_LEVELS
from .paths import GENERATED_DIR
from .validation import parse_scenario

DEFAULT_SEED = 42
DEFAULT_CASES = 20
GENERATOR_VERSION = 1
PATTERNS = {
    "trade-off": "A one-action route costs more than a three-action alternative.",
    "branching": "Two branches reach the same target through different declared grants.",
    "unreachable": "A disabled final weakness leaves the target unreachable.",
    "cyclic": "A directed cycle shares an asset with a route that needs a local privilege change.",
}

ScenarioDocument = dict[str, Any]


def canonical_json(scenario: ScenarioDocument) -> str:
    """Serialize an input document with sorted keys, stable indentation and a trailing newline."""
    return json.dumps(scenario, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"


def _add_link(
    scenario: ScenarioDocument,
    source: str,
    destination: str,
    cost: int,
    *,
    required: str = "guest",
    credential_grant: str | None = None,
    permission_enabled: bool | None = None,
) -> None:
    key = f"{source}-{destination}"
    connection = {
        "id": f"link-{key}", "source_asset_id": source,
        "destination_asset_id": destination, "enabled": True,
    }
    scenario["connections"].append(connection)
    service_id = f"service-{destination}"
    rule = {
        "id": f"move-{key}", "source_asset_id": source,
        "min_privilege": required, "cost": cost,
        "connection_id": connection["id"], "service_id": service_id,
    }
    if credential_grant is None:
        rule.update(family="vulnerable_service", weakness_id=f"weakness-{destination}")
    else:
        credential_id = f"capability-{key}"
        scenario["credentials"].append({
            "id": credential_id, "source_asset_id": source,
            "min_privilege": required, "enabled": True,
            "authorizations": [{"service_id": service_id, "granted_privilege": credential_grant}],
        })
        rule.update(family="credential_login", credential_id=credential_id)
    if permission_enabled is not None:
        permission_id = f"policy-{key}"
        scenario["permissions"].append({
            "id": permission_id, "source_asset_id": source, "destination_asset_id": destination,
            "service_id": service_id, "min_privilege": required, "enabled": permission_enabled,
        })
        rule["permission_id"] = permission_id
    scenario["actions"].append(rule)


def _add_distractors(
    scenario: ScenarioDocument, rng: random.Random, start: str, ambient: list[str], spine: list[str],
) -> None:
    # Connect the additional assets by a rooted, directed tree, then add cross-links.
    attached = [start]
    for asset in ambient:
        _add_link(scenario, rng.choice(attached), asset, rng.randint(1, 5))
        attached.append(asset)

    registered = {
        (link["source_asset_id"], link["destination_asset_id"]) for link in scenario["connections"]
    }
    candidates = [
        (source, destination) for source in attached + spine for destination in ambient
        if source != destination and (source, destination) not in registered
    ]
    for source, destination in rng.sample(candidates, rng.randint(len(ambient) // 2, len(ambient))):
        _add_link(scenario, source, destination, rng.randint(1, 5), permission_enabled=rng.random() < 0.75)


def _build_scenario(rng: random.Random, seed: int, index: int) -> ScenarioDocument:
    assets = [f"node-{number:02d}" for number in range(1, rng.randint(10, 30) + 1)]
    start, target = assets[0], assets[-1]
    goal_privilege = rng.choice(("user", "admin"))
    pattern = tuple(PATTERNS)[(index - 1) % len(PATTERNS)]
    intermediates = assets[1:-1]
    rng.shuffle(intermediates)
    a, b, c = intermediates[:3]
    scenario = {
        "schema_version": 1,
        "id": f"case-{index:02d}",
        "name": f"Generated case {index:02d} ({pattern})",
        "description": PATTERNS[pattern],
        "privilege_levels": list(PRIVILEGE_LEVELS),
        "assets": [{"id": asset, "label": f"Synthetic asset {asset[-2:]}"} for asset in assets],
        "services": [
            {"id": f"service-{asset}", "asset_id": asset, "label": "Modeled service",
             "enabled": True, "login": True}
            for asset in assets
        ],
        "weaknesses": [
            {"id": f"weakness-{asset}", "asset_id": asset, "service_id": f"service-{asset}",
             "granted_privilege": goal_privilege if asset == target else "user",
             "enabled": asset != target or pattern != "unreachable"}
            for asset in assets
        ],
        "connections": [], "credentials": [], "permissions": [], "actions": [],
        "start": {"asset_id": start, "privilege_level": "guest"},
        "goal": {"asset_id": target, "required_privilege": goal_privilege},
        "metadata": {"generator_version": GENERATOR_VERSION, "seed": seed,
                     "case_index": index, "pattern": pattern},
    }

    if pattern == "trade-off":
        _add_link(scenario, start, target, 5)
        _add_link(scenario, start, a, 1)
        _add_link(scenario, a, b, 1, required="user", credential_grant="guest")
        _add_link(scenario, b, target, 1)
    elif pattern == "branching":
        _add_link(scenario, start, a, rng.randint(1, 5))
        _add_link(scenario, a, target, rng.randint(1, 5), required="user",
                  credential_grant=goal_privilege, permission_enabled=True)
        _add_link(scenario, start, b, rng.randint(1, 4))
        _add_link(scenario, b, c, rng.randint(1, 4))
        _add_link(scenario, c, target, rng.randint(1, 4))
    elif pattern == "unreachable":
        _add_link(scenario, start, a, rng.randint(1, 4))
        _add_link(scenario, a, b, rng.randint(1, 4))
        _add_link(scenario, b, target, rng.randint(1, 4))
    else:
        _add_link(scenario, start, a, rng.randint(1, 4))
        _add_link(scenario, a, b, rng.randint(1, 4), required="user", credential_grant="user")
        _add_link(scenario, b, a, rng.randint(1, 4))
        scenario["weaknesses"].append({
            "id": f"local-{b}", "asset_id": b, "service_id": None,
            "granted_privilege": "admin", "enabled": True,
        })
        scenario["actions"].append({
            "id": f"change-{b}", "family": "local_escalation", "source_asset_id": b,
            "min_privilege": "user", "weakness_id": f"local-{b}", "cost": rng.randint(1, 5),
        })
        _add_link(scenario, b, target, rng.randint(1, 4), required="admin",
                  credential_grant=goal_privilege)

    spine_length = 3 if pattern == "branching" else 2
    _add_distractors(scenario, rng, start, intermediates[spine_length:], intermediates[:spine_length])
    return scenario


def generate_scenarios(seed: int = DEFAULT_SEED, cases: int = DEFAULT_CASES) -> tuple[ScenarioDocument, ...]:
    """Build and validate synthetic networks without consuming global randomness."""
    if type(seed) is not int or not -(2**63) <= seed < 2**63:
        raise ValueError("Seed must be a signed 64-bit integer.")
    if type(cases) is not int or not 1 <= cases <= 99:
        raise ValueError("Case count must be an integer from 1 to 99.")
    rng = random.Random(seed)
    scenarios = tuple(_build_scenario(rng, seed, index) for index in range(1, cases + 1))
    for scenario in scenarios:
        parse_scenario(scenario)
    return scenarios


def generate_to_directory(
    seed: int = DEFAULT_SEED, cases: int = DEFAULT_CASES, output_dir: Path = GENERATED_DIR,
) -> tuple[Path, ...]:
    """Save the requested generated cases and return their paths in generation order."""
    scenarios = generate_scenarios(seed, cases)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for scenario in scenarios:
        path = output_dir / f"{scenario['id']}.json"
        path.write_text(canonical_json(scenario), encoding="utf-8", newline="\n")
        paths.append(path)
    return tuple(paths)


def main(argv: list[str] | None = None) -> None:
    """Generate local case files from command-line options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--cases", type=int, default=DEFAULT_CASES)
    parser.add_argument("--output-dir", type=Path, default=GENERATED_DIR)
    arguments = parser.parse_args(argv)
    try:
        paths = generate_to_directory(arguments.seed, arguments.cases, arguments.output_dir)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Generated and validated {len(paths)} scenarios in {arguments.output_dir}.")


if __name__ == "__main__":
    main()
