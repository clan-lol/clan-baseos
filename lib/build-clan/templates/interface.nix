{
  lib,
  ...
}:
let
  types = lib.types;
in
{
  options = {
    # clan.templates.disko
    disko = lib.mkOption {
      type = types.attrsOf (types.submodule { imports = [ ./disko/interface.nix ]; });
      default = { };
      description = ''
        Holds different disko templates.
      '';
    };

    # clan.templates.clan
    clan = lib.mkOption {
      type = types.attrsOf (types.submodule { imports = [ ./clan/interface.nix ]; });
      default = { };
      description = ''
        Holds the different clan templates.
      '';
    };
  };
}
