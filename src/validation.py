"""Strict, bounded loading and validation of synthetic JSON scenarios."""

import json
import re
from collections.abc import Callable, Iterable
from operator import attrgetter
from pathlib import Path
from types import MappingProxyType
from typing import Any, TypeVar

from .models import (
    PRIVILEGE_LEVELS,
    ActionRule,
    Asset,
    AttackState,
    Authorization,
    Connection,
    Credential,
    GoalSpecification,
    Permission,
    Scenario,
    Service,
    Weakness,
)

MAX_BYTES = 2 * 1024 * 1024
MAX_ASSETS = 250
MAX_RECORDS = 2_000
MAX_ACTIONS = 4_000
MAX_AUTHORIZATIONS = 250
MAX_TOTAL_AUTHORIZATIONS = 4_000
ID_PATTERN = re.compile(r"[a-z][a-z0-9_-]{0,63}")
PRIVILEGE_RANK = MappingProxyType({level: rank for rank, level in enumerate(PRIVILEGE_LEVELS)})
T = TypeVar("T")
FieldValidator = Callable[[Any, str], Any]


class ValidationError(ValueError):
    """An unreadable or invalid scenario or query with an actionable message."""


def _object(value: Any, location: str) -> dict[str, Any]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise ValidationError(f"{location} must be a JSON object with string keys.")
    return value


def _id(value: Any, location: str) -> str:
    if type(value) is not str or ID_PATTERN.fullmatch(value) is None:
        raise ValidationError(
            f"{location} must be a 1–64 character identifier starting with a lowercase letter "
            "and using only lowercase ASCII letters, digits, hyphens or underscores."
        )
    return value


def _optional_id(value: Any, location: str) -> str | None:
    return None if value is None else _id(value, location)


def _text(value: Any, location: str, limit: int = 120) -> str:
    if type(value) is not str or len(value) > limit or not value.strip():
        raise ValidationError(f"{location} must be nonempty text (at most {limit} characters).")
    if any(ord(character) < 32 and character not in "\t\r\n" for character in value):
        raise ValidationError(f"{location} contains a control character.")
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise ValidationError(f"{location} contains an unpaired Unicode surrogate.")
    return value


def _description(value: Any, location: str) -> str:
    return _text(value, location, limit=2_000)


def _boolean(value: Any, location: str) -> bool:
    if type(value) is not bool:
        raise ValidationError(f"{location} must be true or false.")
    return value


def _integer(value: Any, location: str, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ValidationError(f"{location} must be an integer from {low} to {high}.")
    return value


def _cost(value: Any, location: str) -> int:
    return _integer(value, location, 1, 5)


def _positive(value: Any, location: str) -> int:
    return _integer(value, location, 1, 2**31 - 1)


def _seed(value: Any, location: str) -> int:
    return _integer(value, location, -(2**63), 2**63 - 1)


def _privilege(value: Any, location: str) -> str:
    if type(value) is not str or value not in PRIVILEGE_RANK:
        raise ValidationError(f"{location} must be one of: {', '.join(PRIVILEGE_LEVELS)}.")
    return value


def _assert_keys(
    record: dict[str, Any], location: str, required: Iterable[str], optional: Iterable[str] = (),
) -> None:
    required = set(required)
    missing = required - record.keys()
    extra = record.keys() - required - set(optional)
    if missing:
        raise ValidationError(f"{location} is missing required field(s): {', '.join(sorted(missing))}.")
    if extra:
        sample = ", ".join(repr(key[:64]) for key in sorted(extra)[:5])
        raise ValidationError(f"{location} has unsupported field(s): {sample}.")


def _record(
    value: Any,
    location: str,
    required: dict[str, FieldValidator],
    optional: dict[str, FieldValidator] | None = None,
) -> dict[str, Any]:
    value = _object(value, location)
    optional = optional or {}
    _assert_keys(value, location, required, optional)
    return {
        key: validator(value[key], f"{location}.{key}")
        for key, validator in (required | optional).items()
        if key in value
    }


def _array(value: Any, location: str, limit: int, *, minimum: int = 0) -> list[Any]:
    if type(value) is not list or not minimum <= len(value) <= limit:
        raise ValidationError(f"{location} must be an array with {minimum} to {limit} records.")
    return value


def _records(
    value: Any,
    location: str,
    constructor: Callable[..., T],
    fields: dict[str, FieldValidator],
    limit: int = MAX_RECORDS,
    *,
    minimum: int = 0,
) -> tuple[T, ...]:
    items = _array(value, location, limit, minimum=minimum)
    return tuple(
        constructor(**_record(item, f"{location}[{index}]", fields))
        for index, item in enumerate(items)
    )


def _authorizations(value: Any, location: str) -> tuple[Authorization, ...]:
    return _records(
        value, location, Authorization, {"service_id": _id, "granted_privilege": _privilege},
        MAX_AUTHORIZATIONS, minimum=1,
    )


ASSET_FIELDS = {"id": _id, "label": _text}
SERVICE_FIELDS = {"id": _id, "asset_id": _id, "label": _text, "enabled": _boolean, "login": _boolean}
CONNECTION_FIELDS = {
    "id": _id, "source_asset_id": _id, "destination_asset_id": _id, "enabled": _boolean,
}
WEAKNESS_FIELDS = {
    "id": _id, "asset_id": _id, "service_id": _optional_id,
    "granted_privilege": _privilege, "enabled": _boolean,
}
CREDENTIAL_FIELDS = {
    "id": _id, "source_asset_id": _id, "min_privilege": _privilege,
    "enabled": _boolean, "authorizations": _authorizations,
}
PERMISSION_FIELDS = CONNECTION_FIELDS | {"service_id": _optional_id, "min_privilege": _privilege}
FAMILY_FIELDS = {
    "vulnerable_service": {"connection_id": _id, "service_id": _id, "weakness_id": _id},
    "local_escalation": {"weakness_id": _id},
    "credential_login": {"connection_id": _id, "service_id": _id, "credential_id": _id},
}
METADATA_FIELDS = {
    "notes": _description, "generator_version": _positive, "seed": _seed,
    "case_index": _positive, "pattern": _text,
}
ROOT_FIELDS = (
    "schema_version", "id", "name", "description", "privilege_levels", "assets", "services",
    "connections", "weaknesses", "credentials", "permissions", "actions", "start", "goal",
)


def _action_family(value: Any, location: str) -> str:
    if type(value) is not str or value not in FAMILY_FIELDS:
        raise ValidationError(f"{location} must be one of: {', '.join(FAMILY_FIELDS)}.")
    return value


ACTION_FIELDS = {
    "id": _id, "family": _action_family, "source_asset_id": _id,
    "min_privilege": _privilege, "cost": _cost,
}


def _actions(value: Any) -> tuple[ActionRule, ...]:
    rules = []
    for index, item in enumerate(_array(value, "actions", MAX_ACTIONS)):
        location = f"actions[{index}]"
        item = _object(item, location)
        if "family" not in item:
            raise ValidationError(f"{location} is missing required field: family.")
        family = _action_family(item["family"], f"{location}.family")
        rules.append(ActionRule(**_record(
            item, location, ACTION_FIELDS | FAMILY_FIELDS[family],
            {"permission_id": _optional_id},
        )))
    return tuple(rules)


def _find(index: dict[str, T], key: str, location: str) -> T:
    if key not in index:
        raise ValidationError(f"{location} refers to unknown ID {key!r}.")
    return index[key]


def _unique(items: Iterable[T], location: str) -> None:
    seen = set()
    for item in items:
        if item in seen:
            raise ValidationError(f"{location} contains a duplicate entry {item!r}.")
        seen.add(item)


def _validate_records(scenario: Scenario) -> None:
    collections = (
        scenario.assets, scenario.services, scenario.connections, scenario.weaknesses,
        scenario.credentials, scenario.permissions, scenario.actions,
    )
    _unique((record.id for group in collections for record in group), "scenario entity IDs")
    assets = {asset.id: asset for asset in scenario.assets}
    services = {service.id: service for service in scenario.services}
    for service in scenario.services:
        _find(assets, service.asset_id, f"service {service.id!r}.asset_id")

    _unique(
        ((link.source_asset_id, link.destination_asset_id) for link in scenario.connections),
        "directed connection endpoints",
    )
    for link in scenario.connections:
        record = f"connection {link.id!r}"
        _find(assets, link.source_asset_id, f"{record}.source_asset_id")
        _find(assets, link.destination_asset_id, f"{record}.destination_asset_id")
        if link.source_asset_id == link.destination_asset_id:
            raise ValidationError(f"{record}.destination_asset_id must differ from its source.")

    for weakness in scenario.weaknesses:
        record = f"weakness {weakness.id!r}"
        _find(assets, weakness.asset_id, f"{record}.asset_id")
        if weakness.service_id is not None:
            service = _find(services, weakness.service_id, f"{record}.service_id")
            if service.asset_id != weakness.asset_id:
                raise ValidationError(f"{record}.service_id must belong to {weakness.asset_id!r}.")

    if sum(len(credential.authorizations) for credential in scenario.credentials) > MAX_TOTAL_AUTHORIZATIONS:
        raise ValidationError(f"credentials may declare at most {MAX_TOTAL_AUTHORIZATIONS} total authorizations.")
    for credential in scenario.credentials:
        record = f"credential {credential.id!r}"
        _find(assets, credential.source_asset_id, f"{record}.source_asset_id")
        _unique((item.service_id for item in credential.authorizations), f"{record}.authorizations")
        for item in credential.authorizations:
            service = _find(services, item.service_id, f"{record}.authorizations.service_id")
            if service.asset_id == credential.source_asset_id or not service.login:
                raise ValidationError(f"{record} authorization {item.service_id!r} must identify a login service on another asset.")

    for permission in scenario.permissions:
        record = f"permission {permission.id!r}"
        _find(assets, permission.source_asset_id, f"{record}.source_asset_id")
        _find(assets, permission.destination_asset_id, f"{record}.destination_asset_id")
        if permission.service_id is None:
            if permission.source_asset_id != permission.destination_asset_id:
                raise ValidationError(f"{record}.service_id is required for a different destination asset.")
        else:
            service = _find(services, permission.service_id, f"{record}.service_id")
            if service.asset_id != permission.destination_asset_id:
                raise ValidationError(f"{record}.service_id must belong to its destination asset.")
            if permission.source_asset_id == permission.destination_asset_id:
                raise ValidationError(f"{record}.service_id must be null for a local permission.")

    _find(assets, scenario.start.asset_id, "start.asset_id")
    _find(assets, scenario.goal.asset_id, "goal.asset_id")
    _validate_action_references(scenario, assets, services)


def _validate_action_references(
    scenario: Scenario, assets: dict[str, Asset], services: dict[str, Service],
) -> None:
    connections = {link.id: link for link in scenario.connections}
    weaknesses = {weakness.id: weakness for weakness in scenario.weaknesses}
    credentials = {credential.id: credential for credential in scenario.credentials}
    permissions = {permission.id: permission for permission in scenario.permissions}
    signature = attrgetter(
        "family", "source_asset_id", "cost", "permission_id",
        "connection_id", "service_id", "weakness_id", "credential_id",
    )
    signatures = {}
    for action in scenario.actions:
        record = f"action {action.id!r}"
        _find(assets, action.source_asset_id, f"{record}.source_asset_id")
        destination = action.source_asset_id
        if action.connection_id is not None and action.service_id is not None:
            connection = _find(connections, action.connection_id, f"{record}.connection_id")
            if connection.source_asset_id != action.source_asset_id:
                raise ValidationError(f"{record}.connection_id must leave {action.source_asset_id!r}.")
            destination = connection.destination_asset_id
            service = _find(services, action.service_id, f"{record}.service_id")
            if service.asset_id != destination:
                raise ValidationError(f"{record}.service_id must belong to destination {destination!r}.")

        minimum = PRIVILEGE_RANK[action.min_privilege]
        if action.permission_id is not None:
            permission = _find(permissions, action.permission_id, f"{record}.permission_id")
            if (
                permission.source_asset_id != action.source_asset_id
                or permission.destination_asset_id != destination
                or permission.service_id != action.service_id
            ):
                raise ValidationError(f"{record}.permission_id must match its source, destination and service.")
            minimum = max(minimum, PRIVILEGE_RANK[permission.min_privilege])

        if action.weakness_id is not None:
            weakness = _find(weaknesses, action.weakness_id, f"{record}.weakness_id")
            if weakness.asset_id != destination or weakness.service_id != action.service_id:
                raise ValidationError(f"{record}.weakness_id must match its destination and service.")
            if action.family == "local_escalation" and PRIVILEGE_RANK[weakness.granted_privilege] <= minimum:
                raise ValidationError(f"{record}.weakness_id must grant strictly higher privilege than its required minimum.")

        if action.credential_id is not None:
            credential = _find(credentials, action.credential_id, f"{record}.credential_id")
            if credential.source_asset_id != action.source_asset_id:
                raise ValidationError(f"{record}.credential_id is only available at {credential.source_asset_id!r}.")
            if not any(item.service_id == action.service_id for item in credential.authorizations):
                raise ValidationError(f"{record}.credential_id is not authorized for service {action.service_id!r}.")
            minimum = max(minimum, PRIVILEGE_RANK[credential.min_privilege])

        conditions = (*signature(action), minimum)
        if conditions in signatures:
            raise ValidationError(f"{record} duplicates the conditions and cost of action {signatures[conditions]!r}.")
        signatures[conditions] = action.id


def parse_scenario(raw: Any) -> Scenario:
    """Validate a decoded scenario and return its deeply immutable model."""
    raw = _object(raw, "scenario")
    _assert_keys(raw, "scenario", ROOT_FIELDS, ("metadata",))
    if type(raw["schema_version"]) is not int or raw["schema_version"] != 1:
        raise ValidationError("scenario.schema_version must be the supported integer version 1.")
    if type(raw["privilege_levels"]) is not list or raw["privilege_levels"] != list(PRIVILEGE_LEVELS):
        raise ValidationError("scenario.privilege_levels must be ['guest', 'user', 'admin'] in that order.")
    scenario = Scenario(
        schema_version=1,
        id=_id(raw["id"], "scenario.id"),
        name=_text(raw["name"], "scenario.name"),
        description=_description(raw["description"], "scenario.description"),
        privilege_levels=PRIVILEGE_LEVELS,
        assets=_records(raw["assets"], "assets", Asset, ASSET_FIELDS, MAX_ASSETS, minimum=1),
        services=_records(raw["services"], "services", Service, SERVICE_FIELDS),
        connections=_records(raw["connections"], "connections", Connection, CONNECTION_FIELDS),
        weaknesses=_records(raw["weaknesses"], "weaknesses", Weakness, WEAKNESS_FIELDS),
        credentials=_records(raw["credentials"], "credentials", Credential, CREDENTIAL_FIELDS),
        permissions=_records(raw["permissions"], "permissions", Permission, PERMISSION_FIELDS),
        actions=_actions(raw["actions"]),
        start=AttackState(**_record(raw["start"], "start", {"asset_id": _id, "privilege_level": _privilege})),
        goal=GoalSpecification(**_record(
            raw["goal"], "goal", {"asset_id": _id, "required_privilege": _privilege},
        )),
        metadata=MappingProxyType(_record(raw.get("metadata", {}), "metadata", {}, METADATA_FIELDS)),
    )
    _validate_records(scenario)
    return scenario


def _unique_keys(items: list[tuple[str, Any]]) -> dict[str, Any]:
    record = {}
    for key, value in items:
        if key in record:
            raise ValidationError(f"JSON repeats object field {key[:64]!r}.")
        record[key] = value
    return record


def _reject_constant(value: str) -> Any:
    raise ValidationError(f"JSON constant {value!r} is not finite.")


def loads_scenario(text: str | bytes) -> Scenario:
    """Decode UTF-8 JSON, enforce the input limit and validate the scenario."""
    if isinstance(text, str):
        if len(text) > MAX_BYTES:
            raise ValidationError(f"Scenario JSON exceeds the {MAX_BYTES:,}-byte limit.")
        try:
            text = text.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValidationError("Scenario JSON contains an unpaired Unicode surrogate.") from exc
    if not isinstance(text, bytes):
        raise ValidationError("Scenario JSON must be UTF-8 text or bytes.")
    if len(text) > MAX_BYTES:
        raise ValidationError(f"Scenario JSON exceeds the {MAX_BYTES:,}-byte limit.")
    try:
        raw = json.loads(
            text.decode("utf-8-sig"), object_pairs_hook=_unique_keys, parse_constant=_reject_constant,
        )
    except UnicodeDecodeError as exc:
        raise ValidationError("Scenario JSON must be encoded as UTF-8.") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Malformed JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}.") from exc
    except RecursionError as exc:
        raise ValidationError("Scenario JSON exceeds the allowed nesting depth.") from exc
    except ValidationError:
        raise
    except ValueError as exc:
        raise ValidationError("Scenario JSON contains an invalid or oversized number.") from exc
    return parse_scenario(raw)


def load_scenario(path: str | Path) -> Scenario:
    """Read a bounded local scenario file and include its path in errors."""
    path = Path(path)
    try:
        with path.open("rb") as file:
            data = file.read(MAX_BYTES + 1)
        return loads_scenario(data)
    except OSError as exc:
        raise ValidationError(f"Cannot read scenario {path}: {exc.strerror or exc}.") from exc
    except ValidationError as exc:
        raise ValidationError(f"{path}: {exc}") from exc
