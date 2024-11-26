{ inputs, ... }:
{
  imports = [ inputs.treefmt-nix.flakeModule ];
  perSystem =
    { self', pkgs, ... }:
    {
      treefmt.projectRootFile = ".git/config";
      treefmt.programs.shellcheck.enable = true;

      treefmt.programs.mypy.enable = true;
      treefmt.programs.nixfmt.enable = true;
      treefmt.programs.nixfmt.package = pkgs.nixfmt-rfc-style;
      treefmt.programs.deadnix.enable = true;
      treefmt.settings.global.excludes = [
        "*.png"
        "*.jpeg"
        "*.gitignore"
        ".vscode/*"
        "*.toml"
        "*.clan-flake"
        "*.code-workspace"
        "*.pub"
        "*.typed"
        "*.age"
        "*.list"
        "*.desktop"
      ];
      treefmt.programs.prettier = {
        enable = true;
        includes = [
          "*.cjs"
          "*.css"
          "*.html"
          "*.js"
          "*.json5"
          "*.jsx"
          "*.mdx"
          "*.mjs"
          "*.scss"
          "*.ts"
          "*.tsx"
          "*.vue"
          "*.yaml"
          "*.yml"
        ];
        excludes = [
          "*/asciinema-player/*"
        ];
      };
      treefmt.programs.mypy.directories =
        {
          "clan-cli" = {
            extraPythonPackages = self'.packages.clan-cli.testDependencies;
            directory = "pkgs/clan-cli";
          };
          "clan-app" = {
            directory = "pkgs/clan-app";
            extraPythonPackages =
              (self'.packages.clan-app.externalTestDeps or [ ]) ++ self'.packages.clan-cli.testDependencies;
            extraPythonPaths = [ "../clan-cli" ];
          };
        }
        // (
          if pkgs.stdenv.isLinux then
            {
              "clan-vm-manager" = {
                directory = "pkgs/clan-vm-manager";
                extraPythonPackages =
                  self'.packages.clan-vm-manager.externalTestDeps ++ self'.packages.clan-cli.testDependencies;
                extraPythonPaths = [ "../clan-cli" ];
              };
            }
          else
            { }
        );
      treefmt.programs.ruff.check = true;
      treefmt.programs.ruff.format = true;
    };
}
