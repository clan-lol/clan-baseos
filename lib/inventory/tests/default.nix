{ clan-core, lib, ... }:
let
  inventory = (
    import ../build-inventory {

      inherit lib clan-core;
    }
  );
  inherit (inventory) buildInventory;
in
{
  test_inventory_empty =
    let
      compiled = buildInventory {
        inventory = { };
        directory = ./.;
      };
    in
    {
      # Empty inventory should return an empty module
      expr = compiled.machines;
      expected = { };
    };
  test_inventory_role_resolve =
    let
      compiled = buildInventory {
        directory = ./.;
        inventory = {
          modules = clan-core.clanModules;
          services = {
            borgbackup.instance_1 = {
              roles.server.machines = [ "backup_server" ];
              roles.client.machines = [
                "client_1_machine"
                "client_2_machine"
              ];
            };
          };
          machines = {
            "backup_server" = { };
            "client_1_machine" = { };
            "client_2_machine" = { };
          };
        };
      };
    in
    {
      expr = {
        m1 = (compiled.machines."backup_server").compiledServices.borgbackup.matchedRoles;
        m2 = (compiled.machines."client_1_machine").compiledServices.borgbackup.matchedRoles;
        m3 = (compiled.machines."client_2_machine").compiledServices.borgbackup.matchedRoles;
        inherit ((compiled.machines."client_2_machine").compiledServices.borgbackup)
          resolvedRolesPerInstance
          ;
      };

      expected = {
        m1 = [
          "server"
        ];
        m2 = [
          "client"
        ];
        m3 = [
          "client"
        ];
        resolvedRolesPerInstance = {
          instance_1 = {
            client = {
              machines = [
                "client_1_machine"
                "client_2_machine"
              ];
            };
            server = {
              machines = [ "backup_server" ];
            };
          };
        };
      };
    };
  test_inventory_tag_resolve =
    let
      configs = buildInventory {
        directory = ./.;
        inventory = {
          modules = clan-core.clanModules;
          services = {
            borgbackup.instance_1 = {
              roles.client.tags = [ "backup" ];
            };
          };
          machines = {
            "not_used_machine" = { };
            "client_1_machine" = {
              tags = [ "backup" ];
            };
            "client_2_machine" = {
              tags = [ "backup" ];
            };
          };
        };
      };
    in
    {
      expr = configs.machines.client_1_machine.compiledServices.borgbackup.resolvedRolesPerInstance;
      expected = {
        instance_1 = {
          client = {
            machines = [
              "client_1_machine"
              "client_2_machine"
            ];
          };
          server = {
            machines = [ ];
          };
        };
      };
    };

  test_inventory_multiple_roles =
    let
      configs = buildInventory {
        directory = ./.;
        inventory = {
          modules = clan-core.clanModules;
          services = {
            borgbackup.instance_1 = {
              roles.client.machines = [ "machine_1" ];
              roles.server.machines = [ "machine_1" ];
            };
          };
          machines = {
            "machine_1" = { };
          };
        };
      };
    in
    {
      expr = configs.machines.machine_1.compiledServices.borgbackup.matchedRoles;
      expected = [
        "client"
        "server"
      ];
    };

  test_inventory_module_doesnt_exist =
    let
      configs = buildInventory {
        directory = ./.;
        inventory = {
          modules = clan-core.clanModules;
          services = {
            fanatasy.instance_1 = {
              roles.default.machines = [ "machine_1" ];
            };
          };
          machines = {
            "machine_1" = { };
          };
        };
      };
    in
    {
      inherit configs;
      expr = configs.machines.machine_1.machineImports;
      expectedError = {
        type = "ThrownError";
        msg = "ClanModule not found*";
      };
    };

  test_inventory_role_doesnt_exist =
    let
      configs = buildInventory {
        directory = ./.;
        inventory = {
          modules = clan-core.clanModules;
          services = {
            borgbackup.instance_1 = {
              roles.roleXYZ.machines = [ "machine_1" ];
            };
          };
          machines = {
            "machine_1" = { };
          };
        };
      };
    in
    {
      inherit configs;
      expr = configs.machines.machine_1.machineImports;
      expectedError = {
        type = "ThrownError";
        msg = "Roles roleXYZ are not defined in the service borgbackup.";
      };
    };
  # Needs NIX_ABORT_ON_WARN=1
  # So the lib.warn is turned into abort
  test_inventory_tag_doesnt_exist =
    let
      configs = buildInventory {
        directory = ./.;
        inventory = {
          modules = clan-core.clanModules;
          services = {
            borgbackup.instance_1 = {
              roles.client.machines = [ "machine_1" ];
              roles.client.tags = [ "tagXYZ" ];
            };
          };
          machines = {
            "machine_1" = {
              tags = [ "tagABC" ];
            };
          };
        };
      };
    in
    {
      expr = configs.machines.machine_1.machineImports;
      expectedError = {
        type = "Error";
        # TODO: Add warning matching in nix-unit
        msg = ".*";
      };
    };
  test_inventory_disabled_service =
    let
      configs = buildInventory {
        directory = ./.;
        inventory = {
          modules = clan-core.clanModules;
          services = {
            borgbackup.instance_1 = {
              enabled = false;
              roles.client.machines = [ "machine_1" ];
            };
          };
          machines = {
            "machine_1" = {

            };
          };
        };
      };
    in
    {
      inherit configs;
      expr = builtins.filter (v: v != { }) configs.machines.machine_1.machineImports;
      expected = [ ];
    };
}
