# Inventory

`Inventory` is an abstract service layer for consistently configuring distributed services across machine boundaries.

## Concept

Its concept is slightly different to what NixOS veterans might be used to. The inventory is a service definition on a higher level, not a machine configuration. This allows you to define a consistent and coherent service.

The inventory logic will automatically derive the modules and configurations to enable on each machine in your `clan` based on its `role`. This makes it super easy to setup distributed `services` such as Backups, Networking, traditional cloud services, or peer-to-peer based applications.

The following tutorial will walk through setting up a Backup service where the terms `Service` and `Role` will become more clear.

See also: [Inventory API Documentation](../reference/nix-api/inventory.md)

!!! example "Experimental status"
    The inventory implementation is not considered stable yet.
    We are actively soliciting feedback from users.

    Stabilizing the API is a priority.

## Prerequisites

- [x] [Add machines](./adding-machines.md) to your clan.

## Services

The inventory defines `services`. Membership of `machines` is defined via `roles` exclusively.

See each [modules documentation](../reference/clanModules/index.md) for its available roles.

### Adding services to machines

A service can be added to one or multiple machines via `Roles`. clan's `Role` interface provide sane defaults for a module this allows the module author to reduce the configuration overhead to a minimum.

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
