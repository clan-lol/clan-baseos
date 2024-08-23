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

  # map from machine name to service configuration
  # { ${machineName} :: Config }
  serviceConfigs = (
    buildInventory {
      inherit inventory;
      inherit directory;
    }
  );

  machineSettings =
    machineName:
    let
      warn = lib.warn ''
        The use of ./machines/<machine>/settings.json is deprecated.
        If your settings.json is empty, you can safely remove it.
        !!! Consider using the inventory system. !!!

        File: ${directory + /machines/${machineName}/settings.json}

        If there are still features missing in the inventory system, please open an issue on the clan-core repository.
      '';
    in
    # CLAN_MACHINE_SETTINGS_FILE allows to override the settings file temporarily
    # This is useful for doing a dry-run before writing changes into the settings.json
    # Using CLAN_MACHINE_SETTINGS_FILE requires passing --impure to nix eval
    if builtins.getEnv "CLAN_MACHINE_SETTINGS_FILE" != "" then
      warn (builtins.fromJSON (builtins.readFile (builtins.getEnv "CLAN_MACHINE_SETTINGS_FILE")))
    else
      lib.optionalAttrs (builtins.pathExists "${directory}/machines/${machineName}/settings.json") (
        warn (builtins.fromJSON (builtins.readFile (directory + /machines/${machineName}/settings.json)))
      );

  machineImports =
    machineSettings: map (module: clan-core.clanModules.${module}) (machineSettings.clanImports or [ ]);

  # TODO: remove default system once we have a hardware-config mechanism
  nixosConfiguration =
    {
      system ? "x86_64-linux",
      name,
      pkgs ? null,
      extraConfig ? { },
    }:
    nixpkgs.lib.nixosSystem {
      modules =
        let
          settings = machineSettings name;
          facterJson = "${directory}/machines/${name}/facter.json";
          hwConfig = "${directory}/machines/${name}/hardware-configuration.nix";

          facterModules = lib.optionals (builtins.pathExists facterJson) [
            clan-core.inputs.nixos-facter-modules.nixosModules.facter
            { config.facter.reportPath = facterJson; }
          ];
        in
        (machineImports settings)
        ++ facterModules
        ++ [
          {
            # Autoinclude configuration.nix and hardware-configuration.nix
            imports = builtins.filter builtins.pathExists [
              "${directory}/machines/${name}/configuration.nix"
              hwConfig
            ];
            config.warnings = lib.optionals (builtins.all builtins.pathExists [hwConfig facterJson]) [
              ''
                Duplicate hardware facts: '${hwConfig}' and '${facterJson}' exist.
                Using both is not recommended.

                It is recommended to use the hardware facts from '${facterJson}', please remove '${hwConfig}'.
              ''
            ];
          }
          settings
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
              nixpkgs.hostPlatform = lib.mkDefault system;

              # speeds up nix commands by using the nixpkgs from the host system (especially useful in VMs)
              nix.registry.nixpkgs.to = {
                type = "path";
                path = lib.mkDefault nixpkgs;
              };
            }
            // lib.optionalAttrs (pkgs != null) { nixpkgs.pkgs = lib.mkForce pkgs; }
          )
        ];

      specialArgs = {
        inherit clan-core;
      } // specialArgs;
    };

  # TODO: Will be deprecated
  # We must migrate the tests, that create a settings.json to add a machine.
  ##################################################
  testMachines =
    lib.mapAttrs
      (name: _: {
        inherit name;
        system = (machineSettings name).nixpkgs.hostSystem or null;
      })
      (
        lib.filterAttrs (
          machineName: _:
          if builtins.pathExists "${directory}/machines/${machineName}/settings.json" then
            lib.warn ''
              The use of ./machines/<machine>/settings.json is deprecated.
              If your settings.json is empty, you can safely remove it.
              !!! Consider using the inventory system. !!!

              File: ${directory + /machines/${machineName}/settings.json}

              If there are still features missing in the inventory system, please open an issue on the clan-core repository.
            '' true
          else
            false
        ) machinesDirs
      );
  machinesDirs = lib.optionalAttrs (builtins.pathExists "${directory}/machines") (
    builtins.readDir (directory + /machines)
  );
  ##################################################

  allMachines = inventory.machines or { } // config.machines or { } // testMachines;

  supportedSystems = [
    "x86_64-linux"
    "aarch64-linux"
    "riscv64-linux"
    "x86_64-darwin"
    "aarch64-darwin"
  ];

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
            pkgs = pkgsForSystem system;
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
              pkgs = pkgsForSystem system;
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
    { inventory = inventoryLoaded; }
    # Merge the meta attributes from the buildClan function
    { inventory.meta = if config.meta != null then config.meta else { }; }
  ];

  inherit nixosConfigurations;

  clanInternals = {
    inherit (clan-core) clanModules;
    inherit inventoryFile;
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
