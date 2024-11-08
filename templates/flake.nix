{
  outputs =
    { ... }:
    {
      templates = {
        default = {
          description = "Initialize a new clan flake";
          path = ./new-clan;
        };
        minimal = {
          description = "for clans managed via (G)UI";
          path = ./minimal;
        };
        flake-parts = {
          description = "Flake-parts";
          path = ./flake-parts;
        };
        minimal-flake-parts = {
          description = "Minimal flake-parts clan template";
          path = ./minimal-flake-parts;
        };
        machineTemplates = {
          description = "Machine templates";
          path = ./machineTemplates;
        };
      };
    };
}
