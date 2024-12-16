{
  config,
  clan-core,
  nixpkgs,
  lib,
  ...
}:
let
  inherit (config)
    directory
    machines
    pkgsForSystem
    specialArgs
    ;

  inherit (config.clanInternals) inventory;

  inherit (clan-core.lib.inventory) buildInventory;

  supportedSystems = [
    "x86_64-linux"
    "aarch64-linux"
    "riscv64-linux"
    "x86_64-darwin"
    "aarch64-darwin"
  ];

  /*
    An attrset with nixpkgs instantiated for each platform.
    This is important, as:
      1. We don't want to call `pkgsForSystem system` multiple times
      2. We need to fall back to `nixpkgs.legacyPackages.${system}` in case pkgsForSystem returns null
  */
  pkgsFor = lib.genAttrs supportedSystems (
    system:
    let
      pkgs = pkgsForSystem system;
    in
    if pkgs != null then pkgs else nixpkgs.legacyPackages.${system}
  );

  # map from machine name to service configuration
  # { ${machineName} :: Config }
  serviceConfigs = (
    buildInventory {
      inherit inventory;
      inherit directory;
    }
  );

  # TODO: remove default system once we have a hardware-config mechanism
  nixosConfiguration =
    {
      system ? null,
      name,
      pkgs ? null,
      extraConfig ? { },
    }:
    nixpkgs.lib.nixosSystem {
      modules =
        let
          hwConfig = "${directory}/machines/${name}/hardware-configuration.nix";
          diskoConfig = "${directory}/machines/${name}/disko.nix";
        in
        [
          {
            # Autoinclude configuration.nix and hardware-configuration.nix
            imports = builtins.filter builtins.pathExists [
              "${directory}/machines/${name}/configuration.nix"
              hwConfig
              diskoConfig
            ];
          }
          clan-core.nixosModules.clanCore
          extraConfig
          (machines.${name} or { })
          # Inherit the inventory assertions ?
          # { inherit (mergedInventory) assertions; }
          { imports = serviceConfigs.${name} or [ ]; }
          (
            {
              # Settings
              clan.core.clanDir = directory;
              # Inherited from clan wide settings
              # TODO: remove these
              clan.core.name = config.inventory.meta.name;
              clan.core.icon = config.inventory.meta.icon;

              # Machine specific settings
              clan.core.machineName = name;
              networking.hostName = lib.mkDefault name;

              # speeds up nix commands by using the nixpkgs from the host system (especially useful in VMs)
              nix.registry.nixpkgs.to = lib.mkDefault {
                type = "path";
                path = lib.mkDefault nixpkgs;
              };

              # For vars we need to override the system so we run vars
              # generators on the machine that runs `clan vars generate`. If a
              # users is using the `pkgsForSystem`, we don't set
              # nixpkgs.hostPlatform it would conflict with the `nixpkgs.pkgs`
              # option.
              nixpkgs.hostPlatform = lib.mkIf (system != null && (pkgsForSystem system) != null) (
                lib.mkForce system
              );
            }
            // lib.optionalAttrs (pkgs != null) { nixpkgs.pkgs = lib.mkForce pkgs; }
          )
        ];

      specialArgs = {
        inherit clan-core;
      } // specialArgs;
    };

  allMachines = inventory.machines or { } // machines;

  nixosConfigurations = lib.mapAttrs (name: _: nixosConfiguration { inherit name; }) allMachines;

  # This instantiates nixos for each system that we support:
  # configPerSystem = <system>.<machine>.nixosConfiguration
  # We need this to build nixos secret generators for each system
  configsPerSystem = builtins.listToAttrs (
    builtins.map (
      system:
      lib.nameValuePair system (
        lib.mapAttrs (
          name: _:
          nixosConfiguration {
            inherit name system;
            pkgs = pkgsFor.${system};
          }
        ) allMachines
      )
    ) supportedSystems
  );

  configsFuncPerSystem = builtins.listToAttrs (
    builtins.map (
      system:
      lib.nameValuePair system (
        lib.mapAttrs (
          name: _: args:
          nixosConfiguration (
            args
            // {
              inherit name system;
              pkgs = pkgsFor.${system};
            }
          )
        ) allMachines
      )
    ) supportedSystems
  );

  inventoryFile = "${directory}/inventory.json";

  inventoryLoaded =
    if builtins.pathExists inventoryFile then
      (builtins.fromJSON (builtins.readFile inventoryFile))
    else
      { };
in
{
  imports = [
    # Merge the inventory file
    {
      inventory = _: {
        _file = inventoryFile;
        config = inventoryLoaded;
      };
    }
    # TODO: Figure out why this causes infinite recursion
    {
      inventory.machines = lib.optionalAttrs (builtins.pathExists "${directory}/machines") (
        builtins.mapAttrs (_n: _v: { }) (
          (lib.filterAttrs (_: t: t == "directory") (builtins.readDir "${directory}/machines"))
        )
      );
    }
    {
      inventory.machines = lib.mapAttrs (_n: _: { }) config.machines;
    }
    # Merge the meta attributes from the buildClan function
    { inventory.modules = clan-core.clanModules; }
    # config.inventory.meta <- config.meta
    { inventory.meta = config.meta; }
    # Set default for computed tags
    ./computed-tags.nix
  ];

  inherit nixosConfigurations;

  clanInternals = {
    moduleSchemas = clan-core.lib.modules.getModulesSchema config.inventory.modules;
    inherit serviceConfigs;
    inherit (clan-core) clanModules;
    inherit inventoryFile;
    inventoryValuesPrios =
      # Temporary workaround
      builtins.removeAttrs (clan-core.lib.values.getPrios { options = inventory.options; })
        # tags are freeformType which is not supported yet.
        [ "tags" ];
    inventory = config.inventory;
    meta = config.inventory.meta;

    source = "${clan-core}";

    # machine specifics
    machines = configsPerSystem;
    machinesFunc = configsFuncPerSystem;
    all-machines-json = lib.mapAttrs (
      system: configs:
      nixpkgs.legacyPackages.${system}.writers.writeJSON "machines.json" (
        lib.mapAttrs (_: m: m.config.system.clan.deployment.data) configs
      )
    ) configsPerSystem;
  };
}
