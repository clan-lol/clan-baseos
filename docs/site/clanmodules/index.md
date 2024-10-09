# Authoring a clanModule

This site will guide you through authoring your first module. Explaining which conventions must be followed, such that others will have an enjoyable experience and the module can be used with minimal effort.

:fontawesome-solid-road-barrier: :fontawesome-solid-road-barrier: :fontawesome-solid-road-barrier:
Under construction
:fontawesome-solid-road-barrier: :fontawesome-solid-road-barrier: :fontawesome-solid-road-barrier:

!!! Note
    Currently ClanModules should be contributed to the [clan-core repository](https://git.clan.lol/clan/clan-core) via a PR.

    Ad-hoc loading of custom modules is not recommended / supported yet.

## Bootstrapping the `clanModule`

A ClanModule is a specific subset of a [NixOS Module](https://nix.dev/tutorials/module-system/index.html), but it has some constraints and might be used via the [Inventory](../manual/inventory.md) interface.
In fact a `ClanModule` can be thought of as a layer of abstraction on-top of NixOS and/or other ClanModules. It may configure sane defaults and provide an ergonomic interface that is easy to use and can also be used via a UI that is under development currently.

Because ClanModules should be configurable via `json`/`API` all of its interface (`options`) must be serializable.

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
    `README.md` is always required. See section [Readme](#readme) for further details.

    The `roles` folder is strictly required for `features = [ "inventory" ]`.

The clanModule must be registered via the `clanModules` attribute in `clan-core`

```nix title="clanModules/flake-module.nix"
--8<-- "clanModules/flake-module.nix:0:6"
    # Register your new module here
    # ...
```

## Readme

The `README.md` is a required file for all modules. It MUST contain frontmatter in [`toml`](https://toml.io) format.

```markdown
---
description = "Module A"
---

This is the example module that does xyz.
```

See the [frontmatter reference](#frontmatter-reference) for all supported attributes.

## Roles

If the module declares to implement `features = [ "inventory" ]` then it MUST contain a roles directory.

Each `.nix` file in the `roles` directory is added as a role to the inventory service.

Other files can also be placed alongside the `.nix` files

```sh
└── roles
    ├── client.nix
    └── server.nix
```

Adds the roles: `client` and `server`

??? Tip "Good to know"
    Sometimes a `ClanModule` should be usable via both clan's `inventory` concept but also natively as a NixOS module.

    > In the long term, we want most modules to implement support for the inventory,
    > but we are also aware that there are certain low-level modules that always serve as a backend for other higher-level inventory modules.
    > These modules may not want to implement inventory interfaces as they are always used directly by other modules.

    This can be achieved by placing an additional `default.nix` into the root of the ClanModules directory as shown:

    ```sh
    # ModuleA
    ├── README.md
    ├── default.nix
    └── roles
        └── default.nix
    ```

    ```nix title="default.nix"
    {...}:{
        imports = [ ./roles/default.nix ];
    }
    ```

    By utilizing this pattern the module (`moduleA`) can then be imported into any regular NixOS module via:

    ```nix
    {...}:{
        imports  = [ clanModules.moduleA ];
    }
    ```

## Organizing the ClanModule

Each `{role}.nix` is included into the machine if the machine is declared to have the role.

For example

```nix
roles.client.machines = ["MachineA"];
```

Then `roles/client.nix` will be added to the machine `MachineA`.

This behavior makes it possible to split the interface and common code paths when using multiple roles.
In the concrete example of `borgbackup` this allows a `server` to declare a different interface than the corresponding `client`.

The client offers configuration option, to exclude certain local directories from being backed up:

```nix title="roles/client.nix"
# Example client interface
  options.clan.borgbackup.exclude = ...
```

The server doesn't offer any configuration option. Because everything is set-up automatically.

```nix title="roles/server.nix"
# Example server interface
  options.clan.borgbackup = {};
```

Assuming that there is a common code path or a common interface between `server` and `client` this can be structured as:

```nix title="roles/server.nix, roles/client.nix"
{...}: {
    # ...
    imports = [ ../common.nix ];
}
```

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
        Many modules use `roles/default.nix` which registers the role `default`.

        If you are a clan module author and your module has only one role where you cannot determine the name, then we would like you to follow the convention.