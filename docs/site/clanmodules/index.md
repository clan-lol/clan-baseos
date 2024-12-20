# Authoring a clanModule

!!! Danger ":fontawesome-solid-road-barrier: Under Construction :fontawesome-solid-road-barrier:"
    Currently under construction use with caution

    :fontawesome-solid-road-barrier: :fontawesome-solid-road-barrier: :fontawesome-solid-road-barrier:

This site will guide you through authoring your first module. Explaining which conventions must be followed, such that others will have an enjoyable experience and the module can be used with minimal effort.


!!! Tip
    External ClanModules can be ad-hoc loaded via [`clan.inventory.modules`](../reference/nix-api/inventory.md#modules)

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

## Registering the module

=== "User module"

    If the module should be ad-hoc loaded.
    It can be made avilable in any project via the [`clan.inventory.modules`](../reference/nix-api/inventory.md#modules) attribute.

    ```nix title="flake.nix"
    # ...
    buildClan {
        # 1. Add the module to the avilable inventory modules
        inventory.modules = {
            custom-module = ./modules/my_module;
        };
        # 2. Use the module in the inventory
        inventory.services = {
            custom-module.instance_1 = {
                roles.default.machines = [ "machineA" ];
            };
        };
    };
    ```

=== "Upstream module"

    If the module will be contributed to [`clan-core`](https://git.clan.lol/clan-core)
    The clanModule must be registered within the `clanModules` attribute in `clan-core`

    ```nix title="clanModules/flake-module.nix"
    --8<-- "clanModules/flake-module.nix:0:5"
        # Register our new module here
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

See the [Full Frontmatter reference](../reference/clanModules/frontmatter/index.md) further details and all supported attributes.

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

## Adding configuration options

While we recommend to keep the interface as minimal as possible and deriving all required information from the `roles` model it might sometimes be required or convenient to expose customization options beyond `roles`.

The following shows how to add options to your module.

**It is important to understand that every module has its own namespace where it should declare options**

**`clan.{moduleName}`**

???+ Example
    The following example shows how to register options in the module interface

    and how it can be set via the inventory


    ```nix title="/default.nix"
    custom-module = ./modules/custom-module;
    ```

    Since the module is called `custom-module` all of its exposed options should be added to `options.clan.custom-module.*...*`

    ```nix title="custom-module/roles/default.nix"
    {
        options = {
            clan.custom-module.foo = mkOption {
                type = types.str;
                default = "bar";
            };
        };
    }
    ```

    If the module is [registered](#registering-the-module).
    Configuration can be set as follows.

    ```nix title="flake.nix"
    buildClan {
        inventory.services = {
            custom-module.instance_1 = {
                roles.default.machines = [ "machineA" ];
                roles.default.config = {
                    # All configuration here is scoped to `clan.custom-module`
                    foo = "foobar";
                };
            };
        };
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
