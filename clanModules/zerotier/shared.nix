{
  lib,
  config,
  pkgs,
  ...
}:
let
  instanceNames = builtins.attrNames config.clan.inventory.services.zerotier;
  instanceName = builtins.head instanceNames;
  zeroTierInstance = config.clan.inventory.services.zerotier.${instanceName};
  roles = zeroTierInstance.roles;
  controllerMachine = builtins.head roles.controller.machines;
  networkIdPath = "${config.clan.core.clanDir}/machines/${controllerMachine}/facts/zerotier-network-id";
  networkId = if builtins.pathExists networkIdPath then builtins.readFile networkIdPath else null;
  moons = roles.moon.machines;
  moonIps = builtins.foldl' (
    ips: name:
    if builtins.pathExists "${config.clan.core.clanDir}/machines/${name}/facts/zerotier-ip" then
      ips
      ++ [
        (builtins.readFile "${config.clan.core.clanDir}/machines/${name}/facts/zerotier-ip")
      ]
    else
      ips
  ) [ ] moons;
in
{
  options.clan.zerotier = {
    excludeHosts = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ config.clan.core.machineName ];
      description = "Hosts that should be excluded";
    };
    networkIps = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ ];
      description = "Extra zerotier network Ips that should be accepted";
    };
    networkIds = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ ];
      description = "Extra zerotier network Ids that should be accepted";
    };
  };

  config = {
    assertions = [
      {
        assertion = builtins.length instanceNames == 1;
        message = "The zerotier module currently only supports one instance per machine, but found ${builtins.toString instanceNames}";
      }
      {
        assertion = builtins.length roles.controller.machines == 1;
        message = "The zerotier module requires exactly one controller, but found ${builtins.toString roles.controller.machines}";
      }
    ];

    clan.core.networking.zerotier.networkId = networkId;
    clan.core.networking.zerotier.name = instanceName;

    # TODO: in future we want to have the node id of our moons in our facts
    systemd.services.zerotierone.serviceConfig.ExecStartPost = lib.mkIf (moonIps != [ ]) (
      lib.mkAfter [
        "+${pkgs.writeScript "orbit-moons-by-ip" ''
          #!${pkgs.python3.interpreter}
          import json
          import ipaddress
          import subprocess

          def compute_member_id(ipv6_addr: str) -> str:
              addr = ipaddress.IPv6Address(ipv6_addr)
              addr_bytes = bytearray(addr.packed)

              # Extract the bytes corresponding to the member_id (node_id)
              node_id_bytes = addr_bytes[10:16]
              node_id = int.from_bytes(node_id_bytes, byteorder="big")

              member_id = format(node_id, "x").zfill(10)[-10:]

              return member_id
          def main() -> None:
              ips = json.loads(${builtins.toJSON (builtins.toJSON moonIps)})
              for ip in ips:
                  member_id = compute_member_id(ip)
                  res = subprocess.run(["zerotier-cli", "orbit", member_id, member_id])
                  if res.returncode != 0:
                      print(f"Failed to add {member_id} to orbit")
          if __name__ == "__main__":
              main()
        ''}"
      ]
    );

  };
}
