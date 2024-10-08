# Authoring a clanModule

This site will guide you through authoring your first module. Explaining which conventions must be followed, such that others will have an enjoyable experience and the module can be used with minimal effort.

:fontawesome-solid-road-barrier: :fontawesome-solid-road-barrier: :fontawesome-solid-road-barrier:
Under construction
:fontawesome-solid-road-barrier: :fontawesome-solid-road-barrier: :fontawesome-solid-road-barrier:

## Bootstrapping a `clanModule`

A ClanModule is a specific subset of a [NixOS Module](https://nix.dev/tutorials/module-system/index.html), but it has some constraints and might be used via the [Inventory](../manual/inventory.md) interface.

Because ClanModules should be configurable via `json` all of its interface (`options`) must be serializable.

Currently ClanModules should be contributed to the [clan-core repository](https://git.clan.lol/clan/clan-core). Ad-hoc loading of custom modules is not recommended / supported yet.

!!! Tip
    ClanModules interface can be checked by running the json schema converter as follows.

    `nix build .#legacyPackages.x86_64-linux.schemas.inventory`

    If the build succeeds the module is compatible.

## Directory structure

Each module SHOULD be a directory of the following format:

```sh
# Example: borgbackup
clanModules/borgbackup
├── README.md
└── roles
    ├── client.nix
    └── server.nix
```

!!! Tip
    This format is strictly required for `features = [ "inventory" ]`.
    Some module authors might decide to opt-out of [inventory](../manual/inventory.md) usage.

The next step is to register the module via the `clanModules` attribute.

!!! Note
    Currently ClanModules should be contributed to the clan-core repository. Ad-hoc loading modules is not recommended / supported yet.

```nix title="clanModules/flake-module.nix"
--8<-- "clanModules/flake-module.nix:0:6"
    # Register your new module here
    # ...
```

## Readme

The `README.md` is a required file. It MUST contain frontmatter in [`toml`]() format.

```markdown
---
description = "Module A"
---

This is the example module that does xyz.
```

See the [frontmatter reference](#frontmatter-reference) for all supported attributes.

## Roles

Each `.nix` file in the `roles` directory is added as a role to the service.

Other files can be placed alongside the `.nix` files

```sh
└── roles
    ├── client.nix
    └── server.nix
```

Adds the roles: `client` and `server`

## Organizing the ClanModule

Each `{role}.nix` is included into the machine if the machine is declared to have the role.

For example

```nix
roles.client.machines = ["MachineA"];
```

Then `roles/client.nix` will be added to the machine `MachineA`.

## Frontmatter Reference

`description` (**Required** `String`)
:   Short description of the module

`categories` (Optional `[ String ]`)
:   default `[ "Uncategorized" ]`

    Categories are used for Grouping and searching.

    While initial oriented on [freedesktop](https://specifications.freedesktop.org/menu-spec/latest/category-registry.html) the following categories are allowed

    - AudioVideo
    - Audio
    - Video
    - Development
    - Education
    - Game
    - Graphics
    - Social
    - Network
    - Office
    - Science
    - System
    - Settings
    - Utility
    - Uncategorized

`features` (Optional `[ String ]`)
:   default `[]`

    Clans Features that the module implements support for.

    Available feature flags are:

    - `inventory`

    !!! warning "Important"
        Every ClanModule, that specifies `features = [ "inventory" ]` MUST have at least one role.
        Many modules use `roles/default.nix` which registers the role `default`
