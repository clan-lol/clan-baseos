{
  description = "<Put your description here>";

  inputs.clan-core.url = "https://git.clan.lol/clan/clan-core/archive/main.tar.gz";

  outputs =
    { self, clan-core, ... }:
    let
      system = "x86_64-linux";
      pkgs = clan-core.inputs.nixpkgs.legacyPackages.${system};
      # Usage see: https://docs.clan.lol
      clan = clan-core.lib.buildClan {
        directory = self;
        meta.name = "__CHANGE_ME__"; # Ensure this is internet wide unique.

        # Distributed services, uncomment to enable.
        # inventory = {
        #   services = {
        #     # This example configures a BorgBackup service
        #     # Check: https://docs.clan.lol/reference/clanModules which ones are available in Inventory
        #     borgbackup.instance_1 = {
        #       roles.server.machines = [ "jon" ];
        #       roles.client.machines = [ "sara" ];
        #     };
        #   };
        # };

        # Prerequisite: boot into the installer
        # See: https://docs.clan.lol/getting-started/installer
        # local> mkdir -p ./machines/machine1
        # local> Edit ./machines/machine1/configuration.nix to your liking
        machines = {
          # "jon" will be the hostname of the machine
          jon = {
            imports = [
              ./modules/shared.nix
              ./modules/disko.nix
              ./machines/jon/configuration.nix
            ];

            nixpkgs.hostPlatform = system;

            # Set this for clan commands use ssh i.e. `clan machines update`
            # If you change the hostname, you need to update this line to root@<new-hostname>
            # This only works however if you have avahi running on your admin machine else use IP
            clan.core.networking.targetHost = pkgs.lib.mkDefault "root@jon";

            # ssh root@flash-installer.local lsblk --output NAME,ID-LINK,FSTYPE,SIZE,MOUNTPOINT
            disko.devices.disk.main.device = "/dev/disk/by-id/__CHANGE_ME__";

            # IMPORTANT! Add your SSH key here
            # e.g. > cat ~/.ssh/id_ed25519.pub
            users.users.root.openssh.authorizedKeys.keys = throw ''
              Don't forget to add your SSH key here!
              users.users.root.openssh.authorizedKeys.keys = [ "<YOUR SSH_KEY>" ]
            '';

            # Zerotier needs one controller to accept new nodes. Once accepted
            # the controller can be offline and routing still works.
            clan.core.networking.zerotier.controller.enable = true;
          };
          # "sara" will be the hostname of the machine
          sara = {
            imports = [
              ./modules/shared.nix
              ./modules/disko.nix
              ./machines/sara/configuration.nix
            ];

            nixpkgs.hostPlatform = system;

            # Set this for clan commands use ssh i.e. `clan machines update`
            # If you change the hostname, you need to update this line to root@<new-hostname>
            # This only works however if you have avahi running on your admin machine else use IP
            clan.core.networking.targetHost = pkgs.lib.mkDefault "root@sara";

            # ssh root@flash-installer.local lsblk --output NAME,ID-LINK,FSTYPE,SIZE,MOUNTPOINT
            disko.devices.disk.main.device = "/dev/disk/by-id/__CHANGE_ME__";

            # IMPORTANT! Add your SSH key here
            # e.g. > cat ~/.ssh/id_ed25519.pub
            users.users.root.openssh.authorizedKeys.keys = throw ''
              Don't forget to add your SSH key here!
              users.users.root.openssh.authorizedKeys.keys = [ "<YOUR SSH_KEY>" ]
            '';

            /*
              After jon is deployed, uncomment the following line
              This will allow sara to share the VPN overlay network with jon
              The networkId is generated by the first deployment of jon
            */
            # clan.core.networking.zerotier.networkId = builtins.readFile ../jon/facts/zerotier-network-id;
          };
        };
      };
    in
    {
      # all machines managed by Clan
      inherit (clan) nixosConfigurations clanInternals;
      # add the Clan cli tool to the dev shell
      devShells.${system}.default = pkgs.mkShell {
        packages = [ clan-core.packages.${system}.clan-cli ];
      };
    };
}
