"""Scenario syntax, structural limits, reference integrity and immutability."""

import json
from dataclasses import FrozenInstanceError

import pytest

from src.environment import NetworkEnvironment
from src.models import AttackState, GoalSpecification
from src.validation import MAX_BYTES, ValidationError, load_scenario, loads_scenario, parse_scenario


def test_utf8_file_loading_and_immutable_records(model_data, tmp_path):
    file = tmp_path / "scenario.json"
    file.write_text(json.dumps(model_data), encoding="utf-8-sig")
    model = load_scenario(file)
    assert model.start == AttackState("a", "user")
    assert model.goal == GoalSpecification("c", "admin")
    assert model.services[0].label == "Input study"
    assert model.credentials[0].authorizations[0].service_id == "service-c"
    assert model.privilege_levels == ("guest", "user", "admin")
    with pytest.raises(FrozenInstanceError):
        model.connections[0].enabled = False
    with pytest.raises(TypeError):
        model.metadata["notes"] = "Changed"
    model_data["assets"][0]["label"] = "Changed"
    assert model.assets[0].label == "A"


def test_missing_file_reports_path(tmp_path):
    with pytest.raises(ValidationError, match=r"Cannot read scenario .*missing.json"):
        load_scenario(tmp_path / "missing.json")


@pytest.mark.parametrize(
    ("content", "error"),
    [
        ('{"x": 1', r"Malformed JSON at line 1, column"),
        ('{"id": "a", "id": "b"}', r"JSON repeats object field 'id'"),
        ('{"value": NaN}', r"NaN.*not finite"),
        ('{"value": Infinity}', r"Infinity.*not finite"),
        ('{"value": -Infinity}', r"Infinity.*not finite"),
        (b"\xff", "encoded as UTF-8"),
        ("[" * 10_000 + "]" * 10_000, "nesting depth"),
        (b" " * (MAX_BYTES + 1), "byte limit"),
        ("[]", "scenario must be a JSON object"),
    ],
    ids=("syntax", "duplicate-key", "nan", "infinity", "negative-infinity", "utf8", "nesting", "size", "root-type"),
)
def test_invalid_json_rejected(content, error):
    with pytest.raises(ValidationError, match=error):
        loads_scenario(content)


@pytest.mark.parametrize("cost", [0, -1, 6, 1.5, 3.0, "1", True, False, float("inf"), float("nan")])
def test_invalid_costs_are_reported_at_the_rule(model_data, cost):
    model_data["actions"][0]["cost"] = cost
    with pytest.raises(ValidationError, match=r"actions\[0\]\.cost must be an integer from 1 to 5"):
        parse_scenario(model_data)


@pytest.mark.parametrize(
    ("key", "value", "error"),
    [
        ("schema_version", 2, "supported integer version 1"),
        ("schema_version", True, "supported integer version 1"),
        ("privilege_levels", ["guest", "admin", "user"], "in that order"),
        ("assets", [], "1 to 250 records"),
        ("assets", [{}] * 251, "1 to 250 records"),
        ("services", {}, "services must be an array"),
        ("metadata", {"notes": {"host": "example"}}, r"metadata.notes must be nonempty text"),
        ("metadata", {"hostname": "example"}, r"metadata has unsupported field"),
        ("start", {"asset_id": "a", "privilege_level": "root"}, r"start.privilege_level must be"),
        ("start", {"asset_id": "x", "privilege_level": "guest"}, r"start.asset_id.*unknown ID"),
        ("goal", {"asset_id": "x", "required_privilege": "guest"}, r"goal.asset_id.*unknown ID"),
    ],
)
def test_wrong_root_fields(model_data, key, value, error):
    model_data[key] = value
    with pytest.raises(ValidationError, match=error):
        parse_scenario(model_data)


@pytest.mark.parametrize(
    ("collection", "index", "key", "value", "error"),
    [
        ("assets", 0, "id", "a.example", "identifier"),
        ("assets", 0, "id", "service-b", "scenario entity IDs.*duplicate"),
        ("services", 0, "asset_id", "unknown", r"service 'service-b'.asset_id.*unknown ID"),
        ("services", 0, "enabled", "false", r"services\[0\].enabled must be true or false"),
        ("connections", 0, "destination_asset_id", "unknown", r"connection 'link-a-b'.destination_asset_id"),
        ("connections", 0, "destination_asset_id", "a", r"destination_asset_id must differ"),
        ("weaknesses", 0, "service_id", "service-c", r"weakness.*service_id must belong"),
        ("weaknesses", 1, "granted_privilege", "user", r"must grant strictly higher privilege"),
        ("credentials", 0, "authorizations", [], r"authorizations must be an array with 1 to 250"),
        ("credentials", 0, "authorizations", [{"service_id": "missing", "granted_privilege": "user"}], r"credential.*unknown ID"),
        ("credentials", 0, "authorizations", [{"service_id": "service-d", "granted_privilege": "user"}], r"not authorized for service 'service-c'"),
        (
            "credentials", 0, "authorizations", [{"service_id": "service-b", "granted_privilege": "user"}],
            r"must identify a login service on another asset",
        ),
        ("permissions", 0, "service_id", "service-c", r"permission.*service_id must belong"),
        ("permissions", 0, "service_id", None, r"service_id is required"),
        ("permissions", 1, "min_privilege", "admin", r"must grant strictly higher privilege"),
        ("actions", 0, "family", "other", r"actions\[0\].family must be one of"),
        ("actions", 0, "connection_id", "link-b-c", r"connection_id must leave 'a'"),
        ("actions", 0, "connection_id", "missing", r"connection_id.*unknown ID"),
        ("actions", 0, "service_id", "missing", r"service_id.*unknown ID"),
        ("actions", 0, "service_id", "service-c", r"service_id must belong to destination"),
        ("actions", 0, "weakness_id", "missing", r"weakness_id.*unknown ID"),
        ("actions", 0, "weakness_id", "condition-local", r"weakness_id must match"),
        ("actions", 0, "permission_id", "missing", r"permission_id.*unknown ID"),
        ("actions", 0, "permission_id", "allow-b-c", r"permission_id must match"),
        ("actions", 2, "credential_id", "missing", r"credential_id.*unknown ID"),
        ("actions", 2, "command", "placeholder", r"unsupported field"),
    ],
)
def test_invalid_records_identify_fields(model_data, collection, index, key, value, error):
    model_data[collection][index][key] = value
    with pytest.raises(ValidationError, match=error):
        parse_scenario(model_data)


def test_missing_required_fields(model_data):
    del model_data["actions"][1]["weakness_id"]
    with pytest.raises(ValidationError, match=r"actions\[1\].*missing.*weakness_id"):
        parse_scenario(model_data)
    del model_data["goal"]
    with pytest.raises(ValidationError, match="scenario is missing required field.*goal"):
        parse_scenario(model_data)


def test_duplicate_direction_and_equivalent_rules(model_data):
    model_data["connections"].append({**model_data["connections"][0], "id": "duplicate-link"})
    with pytest.raises(ValidationError, match="directed connection endpoints contains a duplicate"):
        parse_scenario(model_data)
    model_data["connections"].pop()
    model_data["actions"].append({**model_data["actions"][0], "id": "duplicate-rule"})
    with pytest.raises(ValidationError, match="duplicates the conditions and cost of action"):
        parse_scenario(model_data)
    model_data["actions"][-1]["min_privilege"] = "user"
    with pytest.raises(ValidationError, match="duplicates the conditions and cost of action"):
        parse_scenario(model_data)
    model_data["actions"][-1]["cost"] = 5
    assert len(parse_scenario(model_data).actions) == 4


def test_duplicate_credential_authorizations_are_ambiguous(model_data):
    authorizations = model_data["credentials"][0]["authorizations"]
    authorizations.append({**authorizations[0], "granted_privilege": "guest"})
    with pytest.raises(ValidationError, match=r"credential.*authorizations contains a duplicate"):
        parse_scenario(model_data)


def test_query_validation_is_explicit(model_data):
    scenario = parse_scenario(model_data)
    environment = NetworkEnvironment(scenario)
    with pytest.raises(ValidationError, match=r"state.asset_id"):
        environment.validate_query(AttackState("absent", "user"), scenario.goal)
    with pytest.raises(ValidationError, match=r"goal.required_privilege"):
        environment.validate_query(scenario.start, GoalSpecification("b", "invalid"))
