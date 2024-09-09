#!/usr/bin/env bash

jsonSchema=$(nix build .#inventory-schema --print-out-paths)/schema.json
nix run .#classgen  "$jsonSchema" "$PKG_ROOT/clan_cli/inventory/classes.py"