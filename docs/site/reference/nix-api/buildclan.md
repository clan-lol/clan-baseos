# BuildClan

This provides an overview of the available arguments of the `buildClan` function.

!!! Note "Flake-parts"
    Each attribute is also available via `clan.<option>`

    For example `clan.inventory = ...;` is equivalent to `buildClan { inventory = ...; }`.


### directory





The directory containing the clan.

A typical directory structure could look like this:

```
.
├── flake.nix
├── assets
├── machines
├── modules
└── sops
```

buildClan argument: `directory`


**Type**: `path`


**Default**:

```nix
"Root directory of the flake"
```

:simple-git: [interface.nix](https://git.clan.lol/clan/clan-core/src/branch/main/lib/build-clan/interface.nix)


### inventory





The `Inventory` submodule.

For details see the [Inventory](./inventory.md) documentation.


**Type**: `submodule`


:simple-git: [interface.nix](https://git.clan.lol/clan/clan-core/src/branch/main/lib/build-clan/interface.nix)


### machines





A mapping of machine names to their nixos configuration.

???+ example

    ```nix
    machines = {
      my-machine = {
        # Your nixos configuration
      };
    };
    ```


**Type**: `module`


**Default**:

```nix
{ }
```

:simple-git: [interface.nix](https://git.clan.lol/clan/clan-core/src/branch/main/lib/build-clan/interface.nix)


### meta





Global information about the clan.


**Type**: `null or (submodule)`


**Default**:

```nix
null
```

:simple-git: [interface.nix](https://git.clan.lol/clan/clan-core/src/branch/main/lib/build-clan/interface.nix)


### meta.name





Needs to be (globally) unique, as this determines the folder name where the flake gets downloaded to.

**Type**: `null or string`


:simple-git: [interface.nix](https://git.clan.lol/clan/clan-core/src/branch/main/lib/build-clan/interface.nix)


### pkgsForSystem





A function that maps from architecture to pkg. `( string -> pkgs )`

If specified this nixpkgs will be only imported once for each system.
This improves performance, but all nipxkgs.* options will be ignored.


**Type**: `function that evaluates to a(n) (null or (attribute set))`


**Default**:

```nix
"Lambda :: String -> { ... } | null"
```

:simple-git: [interface.nix](https://git.clan.lol/clan/clan-core/src/branch/main/lib/build-clan/interface.nix)


### specialArgs





Extra arguments to pass to nixosSystem i.e. useful to make self available

**Type**: `attribute set of raw value`


**Default**:

```nix
{ }
```

:simple-git: [interface.nix](https://git.clan.lol/clan/clan-core/src/branch/main/lib/build-clan/interface.nix)

