{
  lib,
  name,
  ...
}:
let
  types = lib.types;
in
{
  # clan.modules.<module-name>
  options = {
    path = lib.mkOption {
      type = types.path;
      description = ''
        Holds the path to the clan module.
      '';
    };

    name = lib.mkOption {
      type = types.str;
      default = name;
      description = ''
        The name of the module.
      '';
    };
  };
}
