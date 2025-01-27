{
  lib,
  name,
  ...
}:
let
  types = lib.types;
in
{
  # clan.templates.disko.<template-name>
  options = {
    path = lib.mkOption {
      type = types.path;
      description = ''
        Holds the path to the clan template.
      '';
    };

    name = lib.mkOption {
      type = types.str;
      default = name;
      description = ''
        The name of the template.
      '';
    };
  };
}
