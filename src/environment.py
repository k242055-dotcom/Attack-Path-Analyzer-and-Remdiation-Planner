"""Legal transitions and immutable remediation for the declared model."""

from dataclasses import replace

from .models import ActionRule, AttackState, GoalSpecification, Remediation, Scenario, SearchAction
from .validation import PRIVILEGE_RANK, ValidationError

FIX_RECORDS = {
    "disable_weakness": "weaknesses",
    "revoke_credential": "credentials",
    "revoke_permission": "permissions",
    "block_connection": "connections",
}


class NetworkEnvironment:
    """Evaluate only rules in a validated, offline synthetic scenario."""

    def __init__(self, scenario: Scenario):
        self._scenario = scenario
        self._asset_ids = frozenset(asset.id for asset in scenario.assets)
        self._services = {service.id: service for service in scenario.services}
        self._connections = {connection.id: connection for connection in scenario.connections}
        self._weaknesses = {weakness.id: weakness for weakness in scenario.weaknesses}
        self._credentials = {credential.id: credential for credential in scenario.credentials}
        self._permissions = {permission.id: permission for permission in scenario.permissions}
        self._authorizations = {
            (credential.id, authorization.service_id): authorization
            for credential in scenario.credentials
            for authorization in credential.authorizations
        }
        rules_by_source: dict[str, list[ActionRule]] = {}
        for rule in sorted(scenario.actions, key=lambda rule: rule.id):
            rules_by_source.setdefault(rule.source_asset_id, []).append(rule)
        self._rules_by_source = {source: tuple(rules) for source, rules in rules_by_source.items()}

    @property
    def scenario(self) -> Scenario:
        """Expose the immutable model for inspection."""
        return self._scenario

    @property
    def asset_ids(self) -> tuple[str, ...]:
        """Expose sorted asset IDs for controls and deterministic displays."""
        return tuple(sorted(self._asset_ids))

    def _validate_asset(self, asset_id: str, location: str) -> None:
        if type(asset_id) is not str or asset_id not in self._asset_ids:
            raise ValidationError(f"{location} refers to an unknown asset: {asset_id!r}.")

    def _validate_privilege(self, level: str, location: str) -> None:
        if type(level) is not str or level not in PRIVILEGE_RANK:
            raise ValidationError(f"{location} must be one of: {', '.join(self.scenario.privilege_levels)}.")

    def _validate_state(self, state: AttackState) -> None:
        if not isinstance(state, AttackState):
            raise ValidationError("Current state must be an AttackState.")
        self._validate_asset(state.asset_id, "state.asset_id")
        self._validate_privilege(state.privilege_level, "state.privilege_level")

    def validate_query(self, start: AttackState, goal: GoalSpecification) -> None:
        """Check user-selected assets and levels before timing a search."""
        self._validate_state(start)
        if not isinstance(goal, GoalSpecification):
            raise ValidationError("Goal must be a GoalSpecification.")
        self._validate_asset(goal.asset_id, "goal.asset_id")
        self._validate_privilege(goal.required_privilege, "goal.required_privilege")

    def goal_test(self, state: AttackState, goal: GoalSpecification) -> bool:
        """Check whether a valid state meets a valid target and minimum privilege."""
        return state.asset_id == goal.asset_id and (
            PRIVILEGE_RANK[state.privilege_level] >= PRIVILEGE_RANK[goal.required_privilege]
        )

    def successors(self, state: AttackState) -> tuple[SearchAction, ...]:
        """Return legal actions in stable ascending rule ID order."""
        self._validate_state(state)
        successors = []
        for rule in self._rules_by_source.get(state.asset_id, ()):
            action = self._transition(rule, state)
            if action is not None:
                successors.append(action)
        return tuple(successors)

    def _transition(self, rule: ActionRule, state: AttackState) -> SearchAction | None:
        """Check the rule's privilege and enabled component preconditions."""
        connection = self._connections.get(rule.connection_id)
        service = self._services.get(rule.service_id)
        weakness = self._weaknesses.get(rule.weakness_id)
        credential = self._credentials.get(rule.credential_id)
        permission = self._permissions.get(rule.permission_id)
        required_rank = PRIVILEGE_RANK[rule.min_privilege]

        if any(
            not component.enabled
            for component in (connection, service, weakness, credential, permission)
            if component is not None
        ):
            return None
        for component in (permission, credential):
            if component is not None:
                required_rank = max(required_rank, PRIVILEGE_RANK[component.min_privilege])
        current_rank = PRIVILEGE_RANK[state.privilege_level]
        if current_rank < required_rank:
            return None
        minimum = self.scenario.privilege_levels[required_rank]

        target = state.asset_id if connection is None else connection.destination_asset_id
        if weakness is not None:
            granted = weakness.granted_privilege
            if rule.family == "local_escalation" and PRIVILEGE_RANK[granted] <= current_rank:
                return None
        else:
            # Credential login rules are validated against the exact service authorization.
            granted = self._authorizations[(rule.credential_id, rule.service_id)].granted_privilege

        entities = (
            ("connection_id", rule.connection_id), ("service_id", rule.service_id),
            ("weakness_id", rule.weakness_id), ("credential_id", rule.credential_id),
            ("permission_id", rule.permission_id),
        )
        conditions = [f"Source privilege {state.privilege_level} meets required {minimum}."]
        if connection is not None:
            conditions.append(f"Directed connection {connection.id} is enabled from {state.asset_id} to {target}.")
        if service is not None:
            conditions.append(f"Declared destination service {service.id} is enabled.")
        if weakness is not None:
            conditions.append(f"Declared weakness {weakness.id} is enabled and grants {granted}.")
        if credential is not None:
            conditions.append(
                f"Capability {credential.id} is enabled, accessible here at {credential.min_privilege} or above "
                f"and explicitly authorized for login service {rule.service_id} with grant {granted}."
            )
        if permission is not None:
            conditions.append(f"Permission {permission.id} is enabled and requires {permission.min_privilege} or above.")
        if rule.family == "local_escalation":
            conditions.append(f"Exact local grant {granted} is strictly above {state.privilege_level}.")

        return SearchAction(
            id=rule.id,
            family=rule.family,
            source=state,
            destination=AttackState(target, granted),
            cost=rule.cost,
            explanation=f"Rule {rule.id} permits the modeled change from {state.asset_id}/{state.privilege_level} "
            f"to {target}/{granted}.",
            preconditions=tuple(conditions),
            entity_ids=tuple((field, value) for field, value in entities if value is not None),
            min_privilege=minimum,
        )

    def fixes(self) -> tuple[Remediation, ...]:
        """List enabled records by fix category and ascending record ID."""
        return tuple(
            Remediation(kind, record.id)
            for kind, collection in FIX_RECORDS.items()
            for record in sorted(getattr(self.scenario, collection), key=lambda record: record.id)
            if record.enabled
        )

    def apply_fix(self, fix: Remediation) -> "NetworkEnvironment":
        """Construct a new environment with just the selected record disabled."""
        if not isinstance(fix, Remediation) or type(fix.kind) is not str or fix.kind not in FIX_RECORDS:
            raise ValidationError(f"Unknown remediation kind. Choose one of: {', '.join(FIX_RECORDS)}.")
        collection = FIX_RECORDS[fix.kind]
        records = getattr(self.scenario, collection)
        if not any(record.id == fix.record_id for record in records):
            raise ValidationError(f"Remediation {fix.kind!r} refers to unknown record {fix.record_id!r}.")
        updated = tuple(
            replace(record, enabled=False) if record.id == fix.record_id else record
            for record in records
        )
        return NetworkEnvironment(replace(self.scenario, **{collection: updated}))
