---
description = "Convenient, structured module imports for hosts."
categories = ["Utility"]
features = [ "inventory" ]
---
The importer module allows users to configure importing modules in a flexible and structured way.

It exposes the `extraModules` functionality of the inventory, without any added configuration.

## Usage:

```nix
inventory.services = {
  importer.base = {
    roles.default.tags = [ "all" ];
    roles.default.extraModules = [ "modules/base.nix" ];
  };
  importer.zone1 = {
    roles.default.tags = [ "zone1" ];
    roles.default.extraModules = [ "modules/zone1.nix" ];
  };
};
```

This will import the module `modules/base.nix` to all machines that have the `all` tag,
which by default is every machine managed by the clan.
And also import for all machines tagged with `zone1` the module at `modules/zone1.nix`.
