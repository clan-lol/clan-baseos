{
  outputs =
    { ... }:
    {
      templates = {
        default = {
          description = "Initialize a new clan flake";
          path = ./clan/new-clan;
        };
        minimal = {
          description = "for clans managed via (G)UI";
          path = ./clan/minimal;
        };
        flake-parts = {
          description = "Flake-parts";
          path = ./clan/flake-parts;
        };
        minimal-flake-parts = {
          description = "Minimal flake-parts clan template";
          path = ./clan/minimal-flake-parts;
        };
        machineTemplates = {
          description = "Machine templates";
          path = ./clan/machineTemplates;
        };
      };
    };
}
