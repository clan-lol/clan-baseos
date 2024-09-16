# How to add machines

Clan has two general methods of adding machines

- **Automatic**: Detects every folder in the `machines` folder.
- **Declarative**: Explicit declarations in nix.

## Automatic register

Every machine of the form `machines/{machineName}` will be registered automatically.

Automatically imported:

- [x] ``machines/{machineName}/configuration.nix`
- [x] ``machines/{machineName}/hardware-configuration.nix`
- [x] ``machines/{machineName}/facter.json` Automatically configured, for further information see [nixos-facter](../blog/posts/nixos-facter.md)

## Manual declaration

Machines can also be added manually under `buildClan`, `clan.*` in flake-parts or via [`inventory`](../guides/inventory.md).

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
