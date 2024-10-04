{ lib, ... }:
let
  types = lib.types;

  metaOptionsWith = name: {
    name = lib.mkOption {
      type = types.str;
      default = name;
      description = ''
        Name of the machine or service
      '';
    };
    description = lib.mkOption {
      default = null;
      type = types.nullOr types.str;
      description = ''
        Optional freeform description
      '';
    };
    icon = lib.mkOption {
      default = null;
      type = types.nullOr types.str;
      description = ''
        Under construction, will be used for the UI
      '';
    };
  };

  moduleConfig = lib.mkOption {
    default = { };
    # TODO: use types.deferredModule
    # clan.borgbackup MUST be defined as submodule
    type = types.attrsOf types.anything;
    description = ''
      Configuration of the specific clanModule.

      !!! Note
        Configuration is passed to the nixos configuration scoped to the module.

        ```nix
          clan.<serviceName> = { ... # Config }
        ```
    '';
  };

  extraModulesOption = lib.mkOption {
    description = ''
      List of addtionally imported `.nix` expressions.

      Supported types:

      - **Strings**: Interpreted relative to the 'directory' passed to buildClan.
      - **Paths**: should be relative to the current file.
      - **Any**: Nix expression must be serializable to JSON.

      !!! Note
          **The import only happens if the machine is part of the service or role.**

      Other types are passed through to the nixos configuration.

      ???+ Example
          To import the `special.nix` file

          ```
          . Clan Directory
          ├── flake.nix
          ...
          └── modules
              ├── special.nix
              └── ...
          ```

          ```nix
          {
            extraModules = [ "modules/special.nix" ];
          }
          ```
    '';
    apply = value: if lib.isString value then value else builtins.seq (builtins.toJSON value) value;
    default = [ ];
    type = types.listOf (
      types.oneOf [
        types.str
        types.anything
      ]
    );
  };
in
{

  imports = [ ./assertions.nix ];
  options = {
    assertions = lib.mkOption {
      type = types.listOf types.unspecified;
      internal = true;
      visible = false;
      default = [ ];
    };
    meta = lib.mkOption {
      type = lib.types.submoduleWith {
        modules = [
          ./meta-interface.nix
        ];
      };
    };

    machines = lib.mkOption {
      description = ''
        Machines in the inventory.

        Each machine declared here can be referencd via its `attributeName` by the `inventory.service`s `roles`.
      '';
      default = { };
      type = types.attrsOf (
        types.submodule (
          { name, ... }:
          {
            options = {
              inherit (metaOptionsWith name) name description icon;

              tags = lib.mkOption {
                description = ''
                  List of tags for the machine.

                  The machine can be referenced by its tags in `inventory.services`

                  ???+ Example
                      ```nix
                      inventory.machines.machineA.tags = [ "tag1" "tag2" ];
                      ```

                      ```nix
                      services.borgbackup."instance_1".roles.client.tags = [ "tag1" ];
                      ```

                  !!! Note
                      Tags can be used to determine the membership of the machine in the services.
                      Without changing the service configuration, the machine can be added to a service by adding the correct tags to the machine.

                '';
                default = [ ];
                apply = lib.unique;
                type = types.listOf types.str;
              };
              system = lib.mkOption {
                default = null;
                type = types.nullOr types.str;
              };
              deploy.targetHost = lib.mkOption {
                description = "Configuration for the deployment of the machine";
                default = null;
                type = types.nullOr types.str;
              };
            };
          }
        )
      );
    };

    services = lib.mkOption {
      description = ''
        Services of the inventory.

        - The first `<name>` is the moduleName. It must be a valid clanModule name.
        - The second `<name>` is an arbitrary instance name.

        ???+ Example
            ```nix
            #        ClanModule name. See the module documentation for the available modules.
            #        ↓          ↓ Instance name, can be anything, some services might use it as a unique identifier.
            services.borgbackup."instance_1" = {
              roles.client.machines = ["machineA"];
            };
            ```

        !!! Note
            Services MUST be added to machines via `roles` exclusively.
            See [`roles.<rolename>.machines`](#servicesrolesmachines) or [`roles.<rolename>.tags`](#servicesrolesmachines) for more information.
      '';
      default = { };
      type = types.attrsOf (
        types.attrsOf (
          types.submodule (
            # instance name
            { name, ... }:
            {
              options.meta = metaOptionsWith name;
              options.extraModules = extraModulesOption;
              options.config = moduleConfig // {
                description = ''
                  Configuration of the specific clanModule.

                  !!! Note
                      Configuration is passed to the nixos configuration scoped to the module.

                      ```nix
                        clan.<serviceName> = { ... # Config }
                      ```

                  ???+ Example

                      For `services.borgbackup` the config is the passed to the machine with the prefix of `clan.borgbackup`.
                      This means all config values are mapped to the `borgbackup` clanModule exclusively (`config.clan.borgbackup`).

                      ```nix
                      {
                        services.borgbackup."instance_1".config = {
                          destinations = [ ... ];
                          # See the 'borgbackup' module docs for all options
                        };
                      }
                      ```

                  !!! Note
                      The module author is responsible for supporting multiple instance configurations in different roles.
                      See each clanModule's documentation for more information.
                '';
              };
              options.machines = lib.mkOption {
                description = ''
                  Attribute set of machines specific config for the service.

                  Will be merged with other service configs, such as the role config and the global config.
                  For machine specific overrides use `mkForce` or other higher priority methods.

                  ???+ Example

                      ```{.nix hl_lines="4-7"}
                      services.borgbackup."instance_1" = {
                        roles.client.machines = ["machineA"];

                        machineA.config = {
                          # Additional specific config for the machine
                          # This is merged with all other config places
                        };
                      };
                      ```
                '';
                default = { };
                type = types.attrsOf (
                  types.submodule {
                    options.extraModules = extraModulesOption;
                    options.config = moduleConfig // {
                      description = ''
                        Additional configuration of the specific machine.

                        See how [`service.<name>.<name>.config`](#servicesconfig) works in general for further information.
                      '';
                    };
                  }
                );
              };
              options.roles = lib.mkOption {
                default = { };
                type = types.attrsOf (
                  types.submodule {
                    options.machines = lib.mkOption {
                      default = [ ];
                      type = types.listOf types.str;
                      example = [ "machineA" ];
                      description = ''
                        List of machines which are part of the role.

                        The machines are referenced by their `attributeName` in the `inventory.machines` attribute set.

                        Memberships are decaled here to determine which machines are part of the service.

                        Alternatively, `tags` can be used to determine the membership, more dynamically.
                      '';
                    };
                    options.tags = lib.mkOption {
                      default = [ ];
                      apply = lib.unique;
                      type = types.listOf types.str;
                      description = ''
                        List of tags which are used to determine the membership of the role.

                        The tags are matched against the `inventory.machines.<machineName>.tags` attribute set.
                        If a machine has at least one tag of the role, it is part of the role.
                      '';
                    };
                    options.config = moduleConfig // {
                      description = ''
                        Additional configuration of the specific role.

                        See how [`service.<name>.<name>.config`](#servicesconfig) works in general for further information.
                      '';
                    };
                    options.extraModules = extraModulesOption;
                  }
                );
              };
            }
          )
        )
      );
    };
  };
}
