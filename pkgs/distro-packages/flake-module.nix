{
  imports = [ ./gui-installer/flake-module.nix ];
  perSystem =
    {
      self',
      lib,
      pkgs,
      ...
    }:
    {
      checks = lib.mkIf (pkgs.hostPlatform.system == "x86_64-linux") {
        deb-gui-install-test = pkgs.vmTools.runInLinuxVM (
          pkgs.runCommand "deb-gui-install-test" { } ''
            ${pkgs.dpkg}/bin/dpkg -i ${self'.checks.package-gui-installer-deb}/*.deb
            ls -la /usr/bin/clan-app
            ${pkgs.expect}/bin/expect -c '
              spawn /usr/bin/clan-app
              expect "Clan requires Nix to be installed. Would you like to install it now? (y/n)"
              send "n"
              expect "Clan cannot run without Nix. Exiting."
            '
            touch $out
          ''
        );
      };
    };
}
