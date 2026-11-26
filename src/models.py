"""Immutable records for the explicitly declared educational network model."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

PRIVILEGE_LEVELS = ("guest", "user", "admin")
ActionFamily = Literal["vulnerable_service", "local_escalation", "credential_login"]
FixKind = Literal["disable_weakness", "revoke_credential", "revoke_permission", "block_connection"]


@dataclass(frozen=True, order=True)
class AttackState:
    """A location and its current privilege, independent of route history."""

    asset_id: str
    privilege_level: str

    def key(self) -> tuple[str, str]:
        """Return a stable identifier for labels and structural comparisons."""
        return self.asset_id, self.privilege_level


@dataclass(frozen=True)
class GoalSpecification:
    """The target location and minimum privilege the route must reach."""

    asset_id: str
    required_privilege: str


@dataclass(frozen=True)
class Asset:
    """A named location within the synthetic topology."""

    id: str
    label: str


@dataclass(frozen=True)
class Service:
    """A declared service and whether it supports a modeled login."""

    id: str
    asset_id: str
    label: str
    enabled: bool
    login: bool


@dataclass(frozen=True)
class Connection:
    """An explicitly directed link between distinct synthetic assets."""

    id: str
    source_asset_id: str
    destination_asset_id: str
    enabled: bool


@dataclass(frozen=True)
class Weakness:
    """An abstract privilege grant attached to an asset or one of its services."""

    id: str
    asset_id: str
    service_id: str | None
    granted_privilege: str
    enabled: bool


@dataclass(frozen=True)
class Authorization:
    """A credential capability for exactly one destination service and grant."""

    service_id: str
    granted_privilege: str


@dataclass(frozen=True)
class Credential:
    """A synthetic capability available at a single source asset."""

    id: str
    source_asset_id: str
    min_privilege: str
    enabled: bool
    authorizations: tuple[Authorization, ...]


@dataclass(frozen=True)
class Permission:
    """A reusable access condition tied to the action's exact endpoints."""

    id: str
    source_asset_id: str
    destination_asset_id: str
    service_id: str | None
    min_privilege: str
    enabled: bool


@dataclass(frozen=True)
class ActionRule:
    """An explicitly declared transition candidate and its referenced conditions."""

    id: str
    family: ActionFamily
    source_asset_id: str
    min_privilege: str
    cost: int
    permission_id: str | None = None
    connection_id: str | None = None
    service_id: str | None = None
    weakness_id: str | None = None
    credential_id: str | None = None


@dataclass(frozen=True)
class SearchAction:
    """A legal application of a rule to a particular current state."""

    id: str
    family: ActionFamily
    source: AttackState
    destination: AttackState
    cost: int
    explanation: str
    preconditions: tuple[str, ...]
    entity_ids: tuple[tuple[str, str], ...]
    min_privilege: str


@dataclass(frozen=True)
class Remediation:
    """A proposed change to one declared model record."""

    kind: FixKind
    record_id: str


@dataclass(frozen=True)
class Scenario:
    """The validated records and default query for one synthetic network."""

    schema_version: int
    id: str
    name: str
    description: str
    privilege_levels: tuple[str, ...]
    assets: tuple[Asset, ...]
    services: tuple[Service, ...]
    connections: tuple[Connection, ...]
    weaknesses: tuple[Weakness, ...]
    credentials: tuple[Credential, ...]
    permissions: tuple[Permission, ...]
    actions: tuple[ActionRule, ...]
    start: AttackState
    goal: GoalSpecification
    metadata: Mapping[str, str | int]
