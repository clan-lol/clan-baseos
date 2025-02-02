{
  lib,
  nixpkgs,
  clan-core,
  buildClan,
  ...
}:
let
  evalClan = import ./eval.nix {
    inherit lib nixpkgs clan-core;
    self = ./.;
  };
in
#######
{
  test_only_required =
    let
      config = evalClan {
        self = {
          inputs = { };
        };
        directory = ./.;
        meta.name = "test";
        imports = [ ./module.nix ];
      };
    in
    {
      expr = config.inventory ? meta;
      expected = true;
    };

  test_all_simple =
    let
      config = evalClan {
        self = {
          inputs = { };
        };
        directory = ./.;
        machines = { };
        inventory = {
          meta.name = "test";
        };
      };
    in
    {
      expr = config ? inventory;
      expected = true;
    };

  test_outputs_clanInternals =
    let
      config = evalClan {
        self = {
          inputs = { };
        };
        directory = ./.;
        imports = [
          # What the user needs to specif
          {
            directory = ./.;
            inventory.meta.name = "test";
          }

          ./module.nix
          # Explicit output, usually defined by flake-parts
          { options.nixosConfigurations = lib.mkOption { type = lib.types.raw; }; }
        ];
      };
    in
    {
      expr = config.clanInternals.meta;
      expected = {
        description = null;
        icon = null;
        name = "test";
      };
    };

  test_fn_simple =
    let
      result = buildClan {
        self = {
          inputs = { };
        };
        directory = ./.;
        meta.name = "test";
      };
    in
    {
      expr = result.clanInternals.meta;
      expected = {
        description = null;
        icon = null;
        name = "test";
      };
    };

  test_fn_extensiv_meta =
    let
      result = buildClan {
        self = {
          inputs = { };
        };
        directory = ./.;
        meta.name = "test";
        meta.description = "test";
        meta.icon = "test";
        inventory.meta.name = "superclan";
        inventory.meta.description = "description";
        inventory.meta.icon = "icon";
      };
    in
    {
      expr = result.clanInternals.meta;
      expectedError = {
        type = "ThrownError";
        msg = "";
      };
    };

  test_fn_clan_core =
    let
      result = buildClan {
        self = {
          inputs = { };
        };
        directory = ../../.;
        meta.name = "test-clan-core";
      };
    in
    {
      expr = builtins.attrNames result.nixosConfigurations;
      expected = [
        "test-backup"
        "test-inventory-machine"
      ];
    };

  test_buildClan_all_machines =
    let
      result = buildClan {
        self = {
          inputs = { };
        };
        directory = ./.;
        meta.name = "test";
        inventory.machines.machine1.meta.name = "machine1";

        machines.machine2 = { };

      };
    in
    {
      expr = builtins.attrNames result.nixosConfigurations;
      expected = [
        "machine1"
        "machine2"
      ];
    };

  test_buildClan_specialArgs =
    let
      result = buildClan {
        self = {
          inputs = { };
        };
        directory = ./.;
        meta.name = "test";
        specialArgs.foo = "dream2nix";
        machines.machine2 =
          { foo, ... }:
          {
            networking.hostName = foo;
            nixpkgs.hostPlatform = "x86_64-linux";
          };
      };
    in
    {
      expr = result.nixosConfigurations.machine2.config.networking.hostName;
      expected = "dream2nix";
    };
}
