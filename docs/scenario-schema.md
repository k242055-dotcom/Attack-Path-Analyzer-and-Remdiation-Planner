# Scenario JSON schema v1

Store one synthetic scenario per UTF-8 JSON file. The loader also accepts a UTF-8 byte-order mark. Identifiers use `[a-z][a-z0-9_-]{0,63}`. Entity IDs are unique across the record collections in a scenario. References match those IDs exactly. Names, labels and pattern names are nonempty text of up to 120 characters. Descriptions and notes are nonempty text of up to 2,000 characters.

## Top-level fields

| Field | Type and meaning |
| --- | --- |
| `schema_version` | Integer `1` |
| `id` | Scenario identifier |
| `name`, `description` | Scenario text |
| `privilege_levels` | Exactly `["guest", "user", "admin"]`, from least to most privileged |
| `assets` | Asset objects, one or more |
| `services`, `connections`, `weaknesses`, `credentials`, `permissions`, `actions` | Arrays of the objects described below, which may be empty |
| `start` | `asset_id` of an existing asset and `privilege_level` from the hierarchy |
| `goal` | `asset_id` of an existing asset and `required_privilege` from the hierarchy |
| `metadata` | Optional object. Allowed keys are `notes` and `pattern` text, positive integer `generator_version` and `case_index` up to 2³¹−1, and signed 64-bit integer `seed`. |

The query satisfies the goal when the asset matches and the current privilege rank equals or exceeds the required rank. All assets use the same hierarchy. A route can move to a lower level on a different asset when that exact grant is declared.

## Record objects

`enabled` and `login` are JSON Booleans. Each listed field is mandatory unless marked optional. A null ID is written as JSON `null`.

| Collection | Fields | Reference rules |
| --- | --- | --- |
| `assets` | `id`, `label` | One synthetic location per record |
| `services` | `id`, `asset_id`, `label`, `enabled`, `login` | The asset owns the service. `login` declares acceptance of an explicitly authorized capability. |
| `connections` | `id`, `source_asset_id`, `destination_asset_id`, `enabled` | Endpoints are distinct assets. Each ordered pair occurs at most once. A reverse link requires its own record. |
| `weaknesses` | `id`, `asset_id`, `service_id`, `granted_privilege`, `enabled` | A service reference belongs to the weakness's asset. Use null for an asset-local grant. |
| `credentials` | `id`, `source_asset_id`, `min_privilege`, `enabled`, `authorizations` | Each authorization object contains `service_id` and `granted_privilege`. It identifies a login-capable service on a different asset. Each service can appear once per credential. |
| `permissions` | `id`, `source_asset_id`, `destination_asset_id`, `service_id`, `min_privilege`, `enabled` | A remote permission names a service on the destination asset. A local permission uses matching asset IDs and a null service ID. |
| `actions` | `id`, `family`, `source_asset_id`, `min_privilege`, `cost`, optional `permission_id`, and the family fields below | Cost is an integer from 1 through 5. Duplicate candidates share the same family, source, references, effective minimum and cost. |

## Action rules

Every action requires the current asset to match `source_asset_id` and the current level to meet `min_privilege`. If `permission_id` is set, the permission must match the exact source, destination and service and must be enabled. The current level must also meet the permission's minimum. Omit `permission_id` or use null for a candidate without a separate permission condition.

| Family | Additional fields | Effective transition requirements |
| --- | --- | --- |
| `vulnerable_service` | `connection_id`, `service_id`, `weakness_id` | The directed connection leaves the action source. The service belongs to the destination and the weakness applies to that exact service. All three records must be enabled. The destination level is the weakness grant. |
| `local_escalation` | `weakness_id` | The source owns the enabled weakness, which has a null service ID. Its grant must exceed the effective declared minimum at load time and exceed the current level at runtime. The asset remains the same. |
| `credential_login` | `connection_id`, `service_id`, `credential_id` | The directed link, destination login service and credential must be enabled. The credential is declared at the current source and the current level also meets its minimum. Its authorization for that exact service determines the resulting level. |

When multiple conditions set minimum levels, the effective requirement is their maximum. The credential record holds a symbolic capability and service grants. It is available only on its declared source asset. State contains no credential material, prior routes or inventory. Connectivity or a service by itself contributes no legal action.

## Validation and size bounds

The loader rejects malformed or unreadable inputs, duplicate keys, missing or extra fields, unknown references, mismatched endpoints and privileges, duplicate equivalent actions and wrong field types. Disabled records are valid declarations and block actions that depend on them at runtime. An absent referenced record invalidates the scenario regardless of its intended status. A Boolean, fractional, nonfinite or out-of-range cost is invalid.

Limits are 2 MiB per file, 250 assets, 2,000 records per other collection except 4,000 actions, 250 authorizations per credential and 4,000 authorizations in total. There must be at least one authorization in each credential. Use synthetic IDs and text throughout.

## Complete example

This example declares one directed connection and one service on the destination. The action links the connection to the service and its explicitly declared weakness. Its cost is 2. The start meets the source requirement at `guest` and the action grants `user` on `archive`, meeting the goal.

```json
{
  "schema_version": 1,
  "id": "archive_example",
  "name": "Archive example",
  "description": "An explicitly declared route to a synthetic archive.",
  "privilege_levels": ["guest", "user", "admin"],
  "assets": [
    {"id": "entry", "label": "Entry"},
    {"id": "archive", "label": "Archive"}
  ],
  "services": [
    {"id": "archive_service", "asset_id": "archive", "label": "Archive service", "enabled": true, "login": false}
  ],
  "connections": [
    {"id": "entry_to_archive", "source_asset_id": "entry", "destination_asset_id": "archive", "enabled": true}
  ],
  "weaknesses": [
    {"id": "archive_grant", "asset_id": "archive", "service_id": "archive_service", "granted_privilege": "user", "enabled": true}
  ],
  "credentials": [],
  "permissions": [],
  "actions": [
    {"id": "reach_archive", "family": "vulnerable_service", "source_asset_id": "entry", "min_privilege": "guest",
     "cost": 2, "connection_id": "entry_to_archive", "service_id": "archive_service", "weakness_id": "archive_grant"}
  ],
  "start": {"asset_id": "entry", "privilege_level": "guest"},
  "goal": {"asset_id": "archive", "required_privilege": "user"},
  "metadata": {"notes": "Disabling archive_grant removes the one permitted transition."}
}
```

An invalid variant changes the action's cost to `true`. The validator reports `actions[0].cost` and the required integer range. Another invalid variant reverses `entry_to_archive` without changing the action. The action's connection then fails the source check. The six [checked examples](../data/scenarios/checked/) include legal cases with all three action families.

## Preview a fix

| Fix selector | Record updated |
| --- | --- |
| `disable_weakness` | Set the identified weakness's `enabled` flag to false |
| `revoke_credential` | Set the identified credential's `enabled` flag to false |
| `revoke_permission` | Set the identified permission's `enabled` flag to false |
| `block_connection` | Set the identified directed connection's `enabled` flag to false |

The preview uses a derived environment and preserves the baseline scenario. A fix only affects actions whose preconditions depend on that specific record. Reachability and route changes apply to the modeled query.
