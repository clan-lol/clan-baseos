# Interface for module authors

Status: proposed

## Context

ClanModules define cross `machine` `services`.
Services can be `instantiated` multiple times.
To make configuration more natural each service instance has multiple `roles` (.i.e. `client`  `server`)

Overall this makes it a 4-Dimensional problem where n-`machines` can have m-`services`, m-`services` can have k-`instances` and k-`instances` can have l-`roles`.

### Problems

Problems with the current way of writing clanModules.

1. No way to retrieve the config of a single service instance
    2. -> We can't really support multiple instances even though the nix module *could* support multiple instances
    3. the "config" of a service MUST be evaluated against the "interface" outside of any machine.
    -> Solution: evaluate each instance config and store it in seperate attributes
3. Can't merge multiple config instances -> Example: https://pad.lassul.us/i9uSspVbRUmiBmsJ8OR1ug#
    -> Propsed change: feed the instance config into a helper that defines the merge behavior
5. Writing modules for multiple instances is cumbersome
    -> Propsed change: Helper utility such as "perInstance"
6. No clearly separated, role based interface that is usable via json based APIs
    1. Currently we just import the module into a test machine and try to figure out what changes
    -> Proposed change: enforce machine agnostic inventory interface definitions

### Some immediate ideas

#### simple idea

Just use another nested attribute set

- `clan.something.borgbackup.instance1 = config`
- `clan.something.borgbackup.instance1 = config`

Problems solved:

- each instance has its own config

Problems not solved:

- Machine independent seperated interface
- Still cumbersome to merge the instances
- Unclear how to get to each config because the interface also depends on the role

#### Improved Idea

- PerInstance: utility that maps over all instances and defines what needs to be set for each instance and receives the instanceConfig as argument.
- GlobalConfig: Some stuff that needs to be set statically on a machine if the service is enabled.

## Proposed Change

Change the ClanModule interface

`client.nix`
```nix
{
  # Allows backwards compatibility
  _class = "clan";

  # Allows importing other service modules
  module.zerotier = {
    # function that receives each instance along with its config and resolved roles
    perInstance =
      {
        # serviceConfig is the config of this instance
        # as described in interface attribute below.
        # Merged without differing priority:
        # service.<instanceName>.config
        # + role.<roleName>.config
        # + machine.<machineName>.config
        serviceConfig,
        # : string
        instanceName,
        # machine :: { name :: string , roles :: listOf string; }
        machine,
        # : { {roleName} :: { machines :: listOf string; } }
        roles,
      ... }:
      {
        nixosModule = {
          config.debug."${instanceName}-client" = serviceConfig;
        };
      };
    # Function that is appplied once for this role
    perService = {
      nixosModule =
        { lib, ... }:
        {
          # Some shared code should be put into a shared file
          # Which is then imported into all/some roles
          imports = [
            ../shared.nix
          ];
          options.debug = lib.mkOption {
            type = lib.types.attrsOf lib.types.raw;
          };
        };
    };

    # Describes the settings how a `client` can be configured.
    # These are the `options` of serviceConfig of a `client`. (Since: This file is called client.nix)
    interface =
      { lib, ... }:
      {
        options.foo = lib.mkOption {
          type = lib.types.str;
          default = "bar";
        };
      };
  };
}
```

## Not Changed! (existing inventory.services for api configuration of clanModules)

```nix
{
    inventory.services = {
        test."instance1" = {
            roles.client.tags = [ "all" ];
            machines.foo.config = { ... };
            roles.client.config = { ... };

        };
        test."instance2" = {
        roles.server.tags = [ "all" ];
        config = { ... };
        };
    };
}
```

We don't propse to change anything here. Because we had no problems with that interface yet.
We even like it because it is very fast to evaluate and can be configured via UI.

### Example of borgbackup before and after

```nix
# client.nix (BEFORE)
{config, ...}:
let
  instances = config.clan.inventory.services.borgbackup or { };
  # roles = { ${role_name} :: { machines :: [string] } }
  allServers = lib.foldlAttrs (
    acc: _instanceName: instanceConfig:
    acc
    ++ (
      if builtins.elem machineName instanceConfig.roles.client.machines then
        instanceConfig.roles.server.machines
      else
        [ ]
    )
  ) [ ] instances;

  machineName = config.clan.core.settings.machine.name;

  cfg = config.clan.borgbackup;
in
{
#  ... Some nixos config
}
```

```nix
# client.nix (AFTER)
{
  _class = "clan";
  perInstance = {instanceName, serviceConfig, machine, roles }: {
    # allServers => roles.server;
    # machineName => machine.name;
    # cfg => serviceConfig;
    nixosModule = {config, ...}: {
    #   ...some nixos config
    }
    # Extendable. I.e. Instances can also define 'vars' or other things later.
  };
}
```
