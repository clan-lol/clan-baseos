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
        A Short description of the module.
      '';
    };
    categories = mkOption {
      default = [ "Uncategorized" ];
      description = ''
        Categories are used for Grouping and searching.

        While initial oriented on [freedesktop](https://specifications.freedesktop.org/menu-spec/latest/category-registry.html) the following categories are allowed
      '';
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
      description = ''
        Clans Features that the module implements support for.

        !!! warning "Important"
            Every ClanModule, that specifies `features = [ "inventory" ]` MUST have at least one role.
            Many modules use `roles/default.nix` which registers the role `default`.

            If you are a clan module author and your module has only one role where you cannot determine the name, then we would like you to follow the convention.
      '';
      type = types.listOf (
        types.enum [
          "inventory"
        ]
      );
    };

    constraints = mkOption {
      default = { };
      description = ''
        Contraints for the module

        The following example requires exactly one `server`
        and supports up to `7` clients

        ```md
        ---
        constraints.roles.server.eq = 1
        constraints.roles.client.max = 7
        ---
        ```
      '';
      type = types.submoduleWith {
        inherit specialArgs;
        modules = [
          ../constraints
        ];
      };
    };
  };
}
