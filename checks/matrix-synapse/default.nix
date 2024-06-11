(import ../lib/container-test.nix) (
  { pkgs, ... }:
  {
    name = "matrix-synapse";

    nodes.machine =
      {
        config,
        self,
        lib,
        ...
      }:
      {
        imports = [
          self.clanModules.matrix-synapse
          self.nixosModules.clanCore
          {
            clanCore.machineName = "machine";
            clanCore.clanDir = ./.;

            services.nginx.virtualHosts."matrix.clan.test" = {
              enableACME = lib.mkForce false;
              forceSSL = lib.mkForce false;
            };
            clan.matrix-synapse.domain = "clan.test";
            clan.matrix-synapse.users.admin.admin = true;
            clan.matrix-synapse.users.someuser = { };

            clanCore.facts.secretStore = "vm";

            # because we use systemd-tmpfiles to copy the secrets, we need to a seperate systemd-tmpfiles call to provison them.
            boot.postBootCommands = "${config.systemd.package}/bin/systemd-tmpfiles --create /etc/tmpfiles.d/00-vmsecrets.conf";

            systemd.tmpfiles.settings."00-vmsecrets" = {
              # run before 00-nixos.conf
              "/etc/secrets" = {
                d.mode = "0700";
                z.mode = "0700";
              };
              "/etc/secrets/synapse-registration_shared_secret" = {
                f.argument = "registration_shared_secret: supersecret";
                z = {
                  mode = "0400";
                  user = "root";
                };
              };
              "/etc/secrets/matrix-password-admin" = {
                f.argument = "matrix-password1";
                z = {
                  mode = "0400";
                  user = "root";
                };
              };
              "/etc/secrets/matrix-password-someuser" = {
                f.argument = "matrix-password2";
                z = {
                  mode = "0400";
                  user = "root";
                };
              };
            };
          }
        ];
      };
    testScript = ''
      start_all()
      machine.wait_for_unit("matrix-synapse")
      machine.succeed("${pkgs.netcat}/bin/nc -z -v ::1 8008")
      machine.succeed("${pkgs.curl}/bin/curl -Ssf -L http://localhost/_matrix/static/ -H 'Host: matrix.clan.test'")

      machine.systemctl("restart matrix-synapse >&2") # check if user creation is idempotent
      machine.execute("journalctl -u matrix-synapse --no-pager >&2")
      machine.wait_for_unit("matrix-synapse")
      machine.succeed("${pkgs.netcat}/bin/nc -z -v ::1 8008")
      machine.succeed("${pkgs.curl}/bin/curl -Ssf -L http://localhost/_matrix/static/ -H 'Host: matrix.clan.test'")
    '';
  }
)
