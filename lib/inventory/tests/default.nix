{ inventory, clan-core, ... }:
let
  inherit (inventory) buildInventory;
in
{
  test_inventory_empty = {
    # Empty inventory should return an empty module
    expr = buildInventory {
      inventory = { };
      directory = ./.;
    };
    expected = { };
  };
  test_inventory_role_imports =
    let
      configs = buildInventory {
        directory = ./.;
        inventory = {
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
        server_imports = (builtins.head configs."backup_server").imports;
        client_1_imports = (builtins.head configs."client_1_machine").imports;
        client_2_imports = (builtins.head configs."client_2_machine").imports;
      };

      expected = {
        server_imports = [
          "${clan-core.clanModules.borgbackup}/roles/server.nix"
        ];
        client_1_imports = [
          "${clan-core.clanModules.borgbackup}/roles/client.nix"
        ];
        client_2_imports = [
          "${clan-core.clanModules.borgbackup}/roles/client.nix"
        ];
      };
    };
  test_inventory_tag_resolve =
    let
      configs = buildInventory {
        directory = ./.;
        inventory = {
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
      expr = {
        # A machine that includes the backup service should have 3 imports
        # - one for some service agnostic properties of the machine itself
        # - One for the service itself (default.nix)
        # - one for the role (roles/client.nix)
        client_1_machine = builtins.length configs.client_1_machine;
        client_2_machine = builtins.length configs.client_2_machine;
        not_used_machine = builtins.length configs.not_used_machine;
      };
      expected = {
        client_1_machine = 6;
        client_2_machine = 6;
        not_used_machine = 3;
      };
    };

  test_inventory_multiple_roles =
    let
      configs = buildInventory {
        directory = ./.;
        inventory = {
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
      expr = {
        machine_1_imports = (builtins.head configs."machine_1").imports;
      };
      expected = {
        machine_1_imports = [
          "${clan-core.clanModules.borgbackup}/roles/client.nix"
          "${clan-core.clanModules.borgbackup}/roles/server.nix"
        ];
      };
    };

  test_inventory_role_doesnt_exist =
    let
      configs = buildInventory {
        directory = ./.;
        inventory = {
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
      expr = configs;
      expectedError = {
        type = "ThrownError";
        msg = "Module doesn't have role.*";
      };
    };
  test_inventory_tag_doesnt_exist =
    let
      configs = buildInventory {
        directory = ./.;
        inventory = {
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
      expr = configs;
      expectedError = {
        type = "ThrownError";
        msg = "no machine with tag '\\w+' found";
      };
    };
}
