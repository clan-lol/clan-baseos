# This script implements the workspace inheritance mechanism described
# here: https://doc.rust-lang.org/cargo/reference/workspaces.html#the-package-table
#
# Please run `mypy --strict`, `black`, and `isort --profile black` on this after editing, thanks!

import sys
from typing import Any, Literal, assert_type

import tomli
import tomli_w


def load_file(path: str) -> dict[str, Any]:
    with open(path, "rb") as f:
        return tomli.load(f)


# This replicates the dependency merging logic from Cargo.
# See `inner_dependency_inherit_with`:
# https://github.com/rust-lang/cargo/blob/4de0094ac78743d2c8ff682489e35c8a7cafe8e4/src/cargo/util/toml/mod.rs#L982
def replace_key(
    workspace_manifest: dict[str, Any],
    table: dict[str, Any],
    section: Literal["package", "dependencies"],
    key: str,
) -> bool:
    if not isinstance(table[key], dict) or table[key].get("workspace") is not True:
        return False
    print("replacing " + key)

    local_dep = table[key]
    del local_dep["workspace"]

    workspace_dep: str | dict[str, Any] = workspace_manifest[section][key]

    if section == "package":
        table[key] = workspace_dep
        return True

    _ = assert_type(section, Literal["dependencies"])

    if isinstance(workspace_dep, str):
        workspace_dep = {"version": workspace_dep}

    final: dict[str, Any] = workspace_dep.copy()

    merged_features = local_dep.pop("features", []) + workspace_dep.get("features", [])
    if merged_features:
        final["features"] = merged_features

    local_default_features = local_dep.pop("default-features", None)
    workspace_default_features = workspace_dep.get("default-features")

    if not workspace_default_features and local_default_features:
        final["default-features"] = True

    optional = local_dep.pop("optional", False)
    if optional:
        final["optional"] = True

    if local_dep:
        msg = f"Unhandled keys in inherited dependency {key}: {local_dep}"
        raise Exception(msg)

    table[key] = final

    # crate_features = local_dep.get("features", [])

    # local_dep.update(workspace_copy)
    # merged_features = crate_features + workspace_copy.get("features", [])
    # if len(merged_features) > len(crate_features):
    #     local_dep["features"] = list(dict.fromkeys(merged_features))

    return True


def replace_dependencies(
    workspace_manifest: dict[str, Any], root: dict[str, Any]
) -> bool:
    changed = False

    for key in ["dependencies", "dev-dependencies", "build-dependencies"]:
        deps = root.get(key, {})
        for k in deps:
            changed |= replace_key(workspace_manifest, deps, "dependencies", k)

    return changed


def main() -> None:
    top_cargo_toml = load_file(sys.argv[2])

    if "workspace" not in top_cargo_toml:
        # If top_cargo_toml is not a workspace manifest, then this script was probably
        # ran on something that does not actually use workspace dependencies
        msg = f"{sys.argv[2]} is not a workspace manifest."
        raise Exception(msg)

    crate_manifest = load_file(sys.argv[1])
    workspace_manifest = top_cargo_toml["workspace"]

    if "workspace" in crate_manifest:
        print(f"{sys.argv[1]} is a workspace manifest, skipping", file=sys.stderr)
        return

    changed = False

    for key in crate_manifest["package"].keys():
        changed |= replace_key(
            workspace_manifest, crate_manifest["package"], "package", key
        )

    changed |= replace_dependencies(workspace_manifest, crate_manifest)

    for value in crate_manifest.get("target", {}).values():
        changed |= replace_dependencies(workspace_manifest, value)

    if crate_manifest.get("lints", {}).get("workspace") is True:
        changed = True
        crate_manifest["lints"] = workspace_manifest["lints"]

    if not changed:
        return print(f"{sys.argv[1]} is unchanged, skipping", file=sys.stderr)

    with open(sys.argv[1], "wb") as f:
        tomli_w.dump(crate_manifest, f)


if __name__ == "__main__":
    main()
