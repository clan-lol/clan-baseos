{
  perSystem =
    {
      pkgs,
      lib,
      self',
      ...
    }:
    {
      # a script that executes all other checks
      packages.impure-checks = pkgs.writeShellScriptBin "impure-checks" ''
        #!${pkgs.bash}/bin/bash
        set -euo pipefail

        unset CLAN_DIR

        export PATH="${
          lib.makeBinPath (
            [
              pkgs.gitMinimal
              pkgs.nix
              pkgs.rsync # needed to have rsync installed on the dummy ssh server
            ]
            ++ self'.packages.clan-cli-full.runtimeDependencies
          )
        }"
        ROOT=$(git rev-parse --show-toplevel)
        cd "$ROOT/pkgs/clan-cli"

        # this disables dynamic dependency loading in clan-cli
        export CLAN_NO_DYNAMIC_DEPS=1

        nix develop "$ROOT#clan-cli" -c bash -c "TMPDIR=/tmp python -m pytest -m impure ./tests $@"
      '';
    };
}
