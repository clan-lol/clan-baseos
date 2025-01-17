# Adding Machines

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
