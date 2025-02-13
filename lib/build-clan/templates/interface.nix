{
  lib,
  ...
}:
let
  inherit (lib) types;

  templateType = types.submodule (
    { name, ... }:
    {
      options.description = lib.mkOption {
        type = types.str;
        default = name;
        description = ''
          The name of the template.
        '';
      };

      options.path = lib.mkOption {
        type = types.path;
        description = ''
          Holds the path to the clan template.
        '';
      };
    }
  );
in
{
  options = {
    # clan.templates.clan
    clan = lib.mkOption {
      type = types.attrsOf templateType;
      default = { };
      description = ''
        Holds the different clan templates.
      '';
    };

    # clan.templates.disko
    disko = lib.mkOption {
      type = types.attrsOf templateType;
      default = { };
      description = ''
        Holds different disko templates.
      '';
    };

    # clan.templates.machine
    machine = lib.mkOption {
      type = types.attrsOf templateType;
      default = { };
      description = ''
        Holds the different machine templates.
      '';
    };
  };
}
