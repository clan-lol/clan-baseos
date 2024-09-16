# Inventory

`Inventory` is an abstract service layer for consistently configuring distributed services across machine boundaries.

See [Inventory API Documentation](../reference/nix-api/inventory.md)

This guide will walk you through setting up a backup-service, where the inventory becomes useful.

## Prerequisites Meta (optional)

Metadata about the clan, will be displayed upfront in the upcomming clan-app, make sure to choose a unique name.

Make sure to set `name` either via `inventory.meta` OR via `clan.meta`.

```{.nix hl_lines="3-8"}
buildClan {
    inventory = {
        meta = {
            name = "Superclan"
            description = "Awesome backups and family stuff"
        };
    };
}
```

## How to add machines

Every machine of the form `machines/{machineName}/configuration.nix` will be registered automatically.

Machines can also be manually added under `inventory.machines` OR via `buildClan` directly.

!!! Note
    It doesn't matter where the machine gets introduced to buildClan - All delarations are valid, duplications are merged.

    However the clan-app (UI) will create machines in the inventory, because it cannot create arbitrary nix code or nixos configs.

In the following example `backup_server` is one machine - it may specify parts of its configuration in different places.

```{.nix hl_lines="3-5 12-20"}
buildClan {
    machines = {
        "backup_server" = {
            # Any valid nixos config
        };
        "jon" = {
            # Any valid nixos config
        };
    };
    inventory = {
        machines = {
            "backup_server" = {
                # Don't include any nixos config here.
                # See the Inventory API Docs for the available attributes.
            };
            "jon" = {
                # Same as above
            };
        };
    };
}
```

## Services

### Available clanModules

Currently the inventory interface is implemented by the following clanModules

- [borgbackup](../reference/clanModules/borgbackup.md)
- [packages](../reference/clanModules/packages.md)
- [single-disk](../reference/clanModules/single-disk.md)

See the respective module documentation for available roles.

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

    ```{.nix hl_lines="14-17"}
    buildClan {
        inventory = {
            machines = {
                "backup_server" = {
                    # Don't include any nixos config here
                    # See inventory.Machines for available options
                };
                "jon" = {
                    # Don't include any nixos config here
                    # See inventory.Machines for available options
                };
            };
            services = {
                borgbackup.instance_1 = {
                    roles.client.machines = [ "jon" ];
                    roles.server.machines = [ "backup_server" ];
                };
            };
        };
    }
    ```

### Scaling the Backup

It is possible to add services to multiple machines via tags. The service instance gets added in the specified role. In this case `role = "client"`

!!! Example "Tags Example"

    ```{.nix hl_lines="9 12 17"}
    buildClan {
        inventory = {
            machines = {
                "backup_server" = {
                    # Don't include any nixos config here
                    # See inventory.Machines for available options
                };
                "jon" = {
                    tags = [ "backup" ];
                };
                "sara" = {
                    tags = [ "backup" ];
                };
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
                borgbackup.instance_1 = {
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
nix build git+https://git.clan.lol/clan/clan-core#inventory-schema
> result
> ├── schema.cue
> └── schema.json
```
