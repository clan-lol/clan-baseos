
Clan has two general methods of adding machines:

- **Automatic**: Detects every folder in the `machines` folder.
- **Declarative**: Explicit declarations in Nix.

## Automatic registration

Every folder `machines/{machineName}` will be registered automatically as a Clan machine.

!!! info "Automatically loaded files"

    The following files are loaded automatically for each Clan machine:

    - [x] `machines/{machineName}/configuration.nix`
    - [x] `machines/{machineName}/hardware-configuration.nix`
    - [x] `machines/{machineName}/facter.json` Automatically configured, for further information see [nixos-facter](https://clan.lol/blog/nixos-facter/)
    - [x] `machines/{machineName}/disko.nix` Automatically loaded, for further information see the [disko docs](https://github.com/nix-community/disko/blob/master/docs/quickstart.md).


## Automatic Imports

The `buildClan` function will automatically import modules if a directory named `<CLAN_ROOT>/imports` exists within the Clan. Below are the conditions for importing inventory modules:

- **Inventory Modules**: Modules located in `<CLAN_ROOT>/imports/inventory` will be automatically imported. Note that only inventory-compatible modules can be used in this location. To be compatible, a module must contain a `roles` folder. 

- **Adding a Module**: To add a module, such as `mymodule`, create a dedicated directory at `<CLAN_ROOT>/imports/inventory/mymodule`, ensuring that it includes a `roles` folder.

For further details on creating Clan modules, please refer to the [Authoring Clan Modules](../clanmodules/index.md) section. 


## Manual declaration

Machines can also be added manually under `buildClan`, `clan.*` in flake-parts or via [`inventory`](../manual/inventory.md).

!!! Note
    It is possible to use `inventory` and `buildClan` together at the same time.

=== "**Individual Machine Configuration**"

    ```{.nix}
    buildClan {
        machines = {
            "jon" = {
                # Any valid nixos config
            };
        };
    }
    ```

=== "**Inventory Configuration**"

    ```{.nix}
    buildClan {
        inventory = {
            machines = {
                "jon" = {
                    # Inventory machines can set tags
                    tags = [ "zone1" ];
                };
            };
        };
    }
    ```
