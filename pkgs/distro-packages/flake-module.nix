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
            while IFS= read -r line; do
              if [[ "$line" == "Clan requires Nix to be installed. Would you like to install it now? (y/n)" ]]; then
                echo "n"
              elif [[ "$line" == "Clan cannot run without Nix. Exiting." ]]; then
                break
              fi
            done < <(/usr/bin/clan-app)
            touch $out
          ''
        );
      };
    };
}
