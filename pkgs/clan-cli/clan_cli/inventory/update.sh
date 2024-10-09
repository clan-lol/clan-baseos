#!/usr/bin/env bash

jsonSchema=$(nix build .#schemas.inventory-schema-abstract --print-out-paths)/schema.json
nix run .#classgen  "$jsonSchema" "$PKG_ROOT/clan_cli/inventory/classes.py"