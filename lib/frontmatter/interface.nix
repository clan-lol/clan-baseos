{
  lib,
  specialArgs,
  ...
}:
let
  inherit (lib) mkOption types;
in
{
  options = {
    description = mkOption {
      type = types.str;
      description = ''

      '';
    };
    categories = mkOption {
      default = [ "Uncategorized" ];
      type = types.listOf (
        types.enum [
          "AudioVideo"
          "Audio"
          "Video"
          "Development"
          "Education"
          "Game"
          "Graphics"
          "Social"
          "Network"
          "Office"
          "Science"
          "System"
          "Settings"
          "Utility"
          "Uncategorized"
        ]
      );
    };
    features = mkOption {
      default = [ ];
      type = types.listOf (
        types.enum [
          "inventory"
        ]
      );
    };

    constraints = mkOption {
      default = { };
      type = types.submoduleWith {
        inherit specialArgs;
        modules = [
          ../constraints
        ];
      };
    };
  };
}
