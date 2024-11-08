# tests for the nixos options to jsonschema converter
# run these tests via `nix-unit ./test.nix`
{
  lib ? (import <nixpkgs> { }).lib,
  slib ? (import ./. { inherit lib; } { }),
}:
{
  testParseOptions = {
    expr = slib.parseModule ./example-interface.nix;
    expected = builtins.fromJSON (builtins.readFile ./example-schema.json);
  };

  testParseNestedOptions =
    let
      evaled = lib.evalModules {
        modules = [ { options.foo.bar = lib.mkOption { type = lib.types.bool; }; } ];
      };
    in
    {
      expr = slib.parseOptions evaled.options { };
      expected = {
        "$schema" = "http://json-schema.org/draft-07/schema#";
        additionalProperties = false;
        properties = {
          foo = {
            additionalProperties = false;
            properties = {
              bar = {
                type = "boolean";
              };
            };
            required = [ "bar" ];
            type = "object";
          };
        };
        type = "object";
      };
    };

  testFreeFormOfInt =
    let
      default = {
        foo = 1;
        bar = 2;
      };
    in
    {
      expr = slib.parseOptions (lib.evalModules {
        modules = [
          {
            freeformType = with lib.types; attrsOf int;
            options = {
              enable = lib.mkEnableOption "enable this";
            };
          }
          default
        ];
      }).options { };
      expected = {
        "$schema" = "http://json-schema.org/draft-07/schema#";
        additionalProperties = {
          type = "integer";
        };
        properties = {
          enable = {
            default = false;
            description = "Whether to enable enable this.";
            examples = [ true ];
            type = "boolean";
          };
        };
        type = "object";
      };
    };

}
