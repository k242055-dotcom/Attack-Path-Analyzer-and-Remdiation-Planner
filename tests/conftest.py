"""Small synthetic fixture shared by validation and transition tests."""

import pytest


@pytest.fixture
def model_data() -> dict:
    """Construct a model whose three transition families can be checked by hand."""
    return {
        "schema_version": 1,
        "id": "test-network",
        "name": "Test network",
        "description": "Three explicitly declared rule families on fictional assets.",
        "privilege_levels": ["guest", "user", "admin"],
        "assets": [{"id": key, "label": key.upper()} for key in ("a", "b", "c", "d")],
        "services": [
            {"id": "service-b", "asset_id": "b", "label": "Input study", "enabled": True, "login": False},
            {"id": "service-c", "asset_id": "c", "label": "Access study", "enabled": True, "login": True},
            {"id": "service-d", "asset_id": "d", "label": "Separate study", "enabled": True, "login": True},
        ],
        "connections": [
            {"id": "link-a-b", "source_asset_id": "a", "destination_asset_id": "b", "enabled": True},
            {"id": "link-b-c", "source_asset_id": "b", "destination_asset_id": "c", "enabled": True},
            {"id": "link-c-d", "source_asset_id": "c", "destination_asset_id": "d", "enabled": True},
        ],
        "weaknesses": [
            {
                "id": "condition-remote", "asset_id": "b", "service_id": "service-b",
                "granted_privilege": "user", "enabled": True,
            },
            {
                "id": "condition-local", "asset_id": "b", "service_id": None,
                "granted_privilege": "admin", "enabled": True,
            },
        ],
        "credentials": [
            {
                "id": "capability-b", "source_asset_id": "b", "min_privilege": "admin", "enabled": True,
                "authorizations": [{"service_id": "service-c", "granted_privilege": "admin"}],
            },
        ],
        "permissions": [
            {
                "id": "allow-a-b", "source_asset_id": "a", "destination_asset_id": "b",
                "service_id": "service-b", "min_privilege": "user", "enabled": True,
            },
            {
                "id": "allow-b-local", "source_asset_id": "b", "destination_asset_id": "b",
                "service_id": None, "min_privilege": "guest", "enabled": True,
            },
            {
                "id": "allow-b-c", "source_asset_id": "b", "destination_asset_id": "c",
                "service_id": "service-c", "min_privilege": "user", "enabled": True,
            },
        ],
        "actions": [
            {
                "id": "rule-a-b", "family": "vulnerable_service", "source_asset_id": "a",
                "min_privilege": "guest", "cost": 2, "permission_id": "allow-a-b",
                "connection_id": "link-a-b", "service_id": "service-b", "weakness_id": "condition-remote",
            },
            {
                "id": "rule-b-local", "family": "local_escalation", "source_asset_id": "b",
                "min_privilege": "user", "cost": 3, "permission_id": "allow-b-local",
                "weakness_id": "condition-local",
            },
            {
                "id": "rule-b-c", "family": "credential_login", "source_asset_id": "b",
                "min_privilege": "guest", "cost": 1, "permission_id": "allow-b-c",
                "connection_id": "link-b-c", "service_id": "service-c", "credential_id": "capability-b",
            },
        ],
        "start": {"asset_id": "a", "privilege_level": "user"},
        "goal": {"asset_id": "c", "required_privilege": "admin"},
        "metadata": {"notes": "Fixture expectation belongs in the tests."},
    }
