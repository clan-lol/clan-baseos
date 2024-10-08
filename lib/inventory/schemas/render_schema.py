"""
Python script to join the abstract inventory schema, with the concrete clan modules
Inventory has slots which are 'Any' type.
We dont want to evaluate the clanModules interface in nix, when evaluating the inventory
"""

import json
import os
from pathlib import Path
from typing import Any

from clan_cli.errors import ClanError

# Get environment variables
INVENTORY_SCHEMA_PATH = Path(os.environ["INVENTORY_SCHEMA_PATH"])

# { [moduleName] :: { [roleName] :: SCHEMA }}
MODULES_SCHEMA_PATH = Path(os.environ["MODULES_SCHEMA_PATH"])

OUT = os.environ.get("out")

if not INVENTORY_SCHEMA_PATH:
    msg = f"Environment variables are not set correctly: INVENTORY_SCHEMA_PATH={INVENTORY_SCHEMA_PATH}."
    raise ClanError(msg)

if not MODULES_SCHEMA_PATH:
    msg = f"Environment variables are not set correctly: MODULES_SCHEMA_PATH={MODULES_SCHEMA_PATH}."
    raise ClanError(msg)

if not OUT:
    msg = f"Environment variables are not set correctly: OUT={OUT}."
    raise ClanError(msg)


def service_roles_to_schema(
    schema: dict[str, Any],
    service_name: str,
    roles: list[str],
    roles_schemas: list[dict[str, Any]],
    # Original service properties: {'config': Schema, 'machines': Schema, 'meta': Schema, 'extraModules': Schema, ...?}
    orig: dict[str, Any],
) -> dict[str, Any]:
    """
    Add roles to the service schema
    """
    role_schema = {}
    for role in roles:
        role_schema[role] = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                **orig["roles"]["additionalProperties"]["properties"],
                "config": {
                    "title": f"{service_name}-config-role-{role}",
                    "oneOf": roles_schemas,
                    "type": "object",
                    "default": {},
                    "additionalProperties": False,
                },
            },
        }

    machines_schema = {
        "type": "object",
        "additionalProperties": {
            "type": "object",
            "properties": {
                **orig["machines"]["additionalProperties"]["properties"],
                "config": {
                    "title": f"{service_name}-config",
                    "oneOf": roles_schemas,
                    "type": "object",
                    "default": {},
                    "additionalProperties": False,
                },
            },
        },
    }

    services["properties"][service_name] = {
        "type": "object",
        "additionalProperties": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                # Original inventory schema
                **orig,
                # Inject the roles schemas
                "roles": {
                    "title": f"{service_name}-roles",
                    "type": "object",
                    "properties": role_schema,
                    "additionalProperties": False,
                },
                "machines": machines_schema,
                "config": {
                    "title": f"{service_name}-config",
                    "oneOf": roles_schemas,
                    "type": "object",
                    "default": {},
                    "additionalProperties": False,
                },
            },
        },
    }

    return schema


if __name__ == "__main__":
    print("Joining inventory schema with modules schema")
    print(f"Inventory schema path: {INVENTORY_SCHEMA_PATH}")
    print(f"Modules schema path: {MODULES_SCHEMA_PATH}")

    modules_schema = {}
    with Path.open(MODULES_SCHEMA_PATH) as f:
        modules_schema = json.load(f)

    inventory_schema = {}
    with Path.open(INVENTORY_SCHEMA_PATH) as f:
        inventory_schema = json.load(f)

    services = inventory_schema["properties"]["services"]
    original_service_props = services["additionalProperties"]["additionalProperties"][
        "properties"
    ].copy()
    # Init the outer services schema
    # Properties (service names) will be filled in the next step
    services = {
        "type": "object",
        "properties": {
            # Service names
        },
        "additionalProperties": False,
    }

    for module_name, roles_schema in modules_schema.items():
        # collect all the roles for the service
        roles_schemas = []
        for role_name, role_schema in roles_schema.items():
            role_schema["title"] = f"{module_name}-config-role-{role_name}"
            roles_schemas.append(role_schema)

        # Add the roles schemas to the service schema
        if roles_schemas:
            roles = list(roles_schema.keys())

            services = service_roles_to_schema(
                services,
                module_name,
                roles,
                roles_schemas,
                original_service_props,
            )

    inventory_schema["properties"]["services"] = services

    outpath = Path(OUT)
    with (outpath / "schema.json").open("w") as f:
        json.dump(inventory_schema, f, indent=2)

    with (outpath / "modules_schemas.json").open("w") as f:
        json.dump(modules_schema, f, indent=2)
