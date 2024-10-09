# Inventory

`Inventory` is an abstract service layer for consistently configuring distributed services across machine boundaries.

See [Inventory API Documentation](../reference/nix-api/inventory.md)

This guide will walk you through setting up a backup service, where the inventory becomes useful.

!!! example "Experimental status"
    The inventory implementation is not considered stable yet.
    We are actively soliciting feedback from users.

    Stabilizing the API is a priority.

## Prerequisites

- [x] [Add machines](./adding-machines.md) to your clan.

## Services

The inventory defines `services`. Membership of `machines` is defined via roles exclusively.

See the each [module documentation](../reference/clanModules/index.md) for available roles.

!!! Note
    It is possible to use any [clanModule](../reference/clanModules/index.md) in the inventory and add machines via
    `roles.default.*`

### Adding services to machines

A module can be added to one or multiple machines via `Roles`. clan's `Role` interface provide sane defaults for a module this allows the module author to reduce the configuration overhead to a minimum.

Each service can still be customized and configured according to the modules options.

- Per instance configuration via `services.<serviceName>.<instanceName>.config`
- Per role configuration via `services.<serviceName>.<instanceName>.roles.<roleName>.config`
- Per machine configuration via `services.<serviceName>.<instanceName>.machines.<machineName>.config`

### Setting up the Backup Service

!!! Example "Borgbackup Example"

    To configure a service it needs to be added to the machine.
    It is required to assign the service (`borgbackup`) an arbitrary instance name. (`instance_1`)

    See also: [Multiple Service Instances](#multiple-service-instances)

    ```{.nix hl_lines="6-7"}
    buildClan {
        inventory = {
            services = {
                borgbackup.instance_1 = {
                    # Machines can be added here.
                    roles.client.machines = [ "jon" ];
                    roles.server.machines = [ "backup_server" ];
                };
            };
        };
    }
    ```

### Scaling the Backup

The inventory allows machines to set Tags

It is possible to add services to multiple machines via tags as shown

!!! Example "Tags Example"

    ```{.nix hl_lines="5 8 14"}
    buildClan {
        inventory = {
            machines = {
                "jon" = {
                    tags = [ "backup" ];
                };
                "sara" = {
                    tags = [ "backup" ];
                };
                # ...
            };
            services = {
                borgbackup.instance_1 = {
                    roles.client.tags = [ "backup" ];
                    roles.server.machines = [ "backup_server" ];
                };
            };
        };
    }
    ```

### Multiple Service Instances

!!! danger "Important"
    Not all modules implement support for multiple instances yet.
    Multiple instance usage could create complexity, refer to each modules documentation, for intended usage.

!!! Example

    In this example `backup_server` has role `client` and `server` in different instances.

    ```{.nix hl_lines="11 14"}
    buildClan {
        inventory = {
            machines = {
                "jon" = {};
                "backup_server" = {};
                "backup_backup_server" = {}
            };
            services = {
                borgbackup.instance_1 = {
                    roles.client.machines = [ "jon" ];
                    roles.server.machines = [ "backup_server" ];
                };
                borgbackup.instance_2 = {
                    roles.client.machines = [ "backup_server" ];
                    roles.server.machines = [ "backup_backup_server" ];
                };
            };
        };
    }
    ```

### API specification

**The complete schema specification is available [here](../reference/nix-api/inventory.md)**

Or it can build anytime via:

```sh
nix build git+https://git.clan.lol/clan/clan-core#schemas.inventory
> result
> ├── schema.cue
> └── schema.json
```
