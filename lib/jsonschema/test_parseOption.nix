# tests for the nixos options to jsonschema converter
# run these tests via `nix-unit ./test.nix`
{
  lib ? (import <nixpkgs> { }).lib,
  slib ? (import ./. { inherit lib; } { }),
}:
let
  description = "Test Description";

  evalType =
    type: default:
    let
      evaledConfig = lib.evalModules {
        modules = [
          {
            options.opt = lib.mkOption {
              inherit type;
              inherit default;
              inherit description;
            };
          }
        ];
      };
    in
    evaledConfig.options.opt;
in
{
  testNoDefaultNoDescription =
    let
      evaledConfig = lib.evalModules {
        modules = [ { options.opt = lib.mkOption { type = lib.types.bool; }; } ];
      };
    in
    {
      expr = slib.parseOption evaledConfig.options.opt;
      expected = {
        type = "boolean";
      };
    };

  testDescriptionIsAttrs =
    let
      evaledConfig = lib.evalModules {
        modules = [
          {
            options.opt = lib.mkOption {
              type = lib.types.bool;
              description = {
                _type = "mdDoc";
                text = description;
              };
            };
          }
        ];
      };
    in
    {
      expr = slib.parseOption evaledConfig.options.opt;
      expected = {
        type = "boolean";
        inherit description;
      };
    };

  testBool =
    let
      default = false;
    in
    {
      expr = slib.parseOption (evalType lib.types.bool default);
      expected = {
        type = "boolean";
        inherit default description;
      };
    };

  testString =
    let
      default = "hello";
    in
    {
      expr = slib.parseOption (evalType lib.types.str default);
      expected = {
        type = "string";
        inherit default description;
      };
    };

  testInteger =
    let
      default = 42;
    in
    {
      expr = slib.parseOption (evalType lib.types.int default);
      expected = {
        type = "integer";
        inherit default description;
      };
    };

  testFloat =
    let
      default = 42.42;
    in
    {
      expr = slib.parseOption (evalType lib.types.float default);
      expected = {
        type = "number";
        inherit default description;
      };
    };

  testEnum =
    let
      default = "foo";
      values = [
        "foo"
        "bar"
        "baz"
      ];
    in
    {
      expr = slib.parseOption (evalType (lib.types.enum values) default);
      expected = {
        enum = values;
        inherit default description;
      };
    };

  testListOfInt =
    let
      default = [
        1
        2
        3
      ];
    in
    {
      expr = slib.parseOption (evalType (lib.types.listOf lib.types.int) default);
      expected = {
        type = "array";
        items = {
          type = "integer";
        };
        inherit default description;
      };
    };

  testListOfUnspecified =
    let
      default = [
        1
        2
        3
      ];
    in
    {
      expr = slib.parseOption (evalType (lib.types.listOf lib.types.unspecified) default);
      expected = {
        type = "array";
        items = {
          type = [
            "boolean"
            "integer"
            "number"
            "string"
            "array"
            "object"
            "null"
          ];
        };
        inherit default description;
      };
    };

  testAttrs =
    let
      default = {
        foo = 1;
        bar = 2;
        baz = 3;
      };
    in
    {
      expr = slib.parseOption (evalType (lib.types.attrs) default);
      expected = {
        type = "object";
        additionalProperties = true;
        inherit default description;
      };
    };

  testAttrsOfInt =
    let
      default = {
        foo = 1;
        bar = 2;
        baz = 3;
      };
    in
    {
      expr = slib.parseOption (evalType (lib.types.attrsOf lib.types.int) default);
      expected = {
        type = "object";
        additionalProperties = {
          type = "integer";
        };
        inherit default description;
      };
    };

  testLazyAttrsOfInt =
    let
      default = {
        foo = 1;
        bar = 2;
        baz = 3;
      };
    in
    {
      expr = slib.parseOption (evalType (lib.types.lazyAttrsOf lib.types.int) default);
      expected = {
        type = "object";
        additionalProperties = {
          type = "integer";
        };
        inherit default description;
      };
    };

  testNullOrBool =
    let
      default = null; # null is a valid value for this type
    in
    {
      expr = slib.parseOption (evalType (lib.types.nullOr lib.types.bool) default);
      expected = {
        oneOf = [
          { type = "null"; }
          { type = "boolean"; }
        ];
        inherit default description;
      };
    };

  testNullOrNullOr =
    let
      default = null; # null is a valid value for this type
    in
    {
      expr = slib.parseOption (evalType (lib.types.nullOr (lib.types.nullOr lib.types.bool)) default);
      expected = {
        oneOf = [
          { type = "null"; }
          {
            oneOf = [
              { type = "null"; }
              { type = "boolean"; }
            ];
          }
        ];
        inherit default description;
      };
    };

  testSubmoduleOption =
    let
      subModule = {
        options.opt = lib.mkOption {
          type = lib.types.bool;
          default = true;
          inherit description;
        };
      };
    in
    {
      expr = slib.parseOption (evalType (lib.types.submodule subModule) { });
      expected = {
        type = "object";
        additionalProperties = false;
        description = "Test Description";
        properties = {
          opt = {
            type = "boolean";
            default = true;
            inherit description;
          };
        };
      };
    };

  testSubmoduleOptionWithoutDefault =
    let
      subModule = {
        options.opt = lib.mkOption {
          type = lib.types.bool;
          inherit description;
        };
      };
    in
    {
      expr = slib.parseOption (evalType (lib.types.submodule subModule) { });
      expected = {
        type = "object";
        additionalProperties = false;
        description = "Test Description";
        properties = {
          opt = {
            type = "boolean";
            inherit description;
          };
        };
        required = [ "opt" ];
      };
    };

  testAttrsOfSubmodule =
    let
      subModule = {
        options.opt = lib.mkOption {
          type = lib.types.bool;
          default = true;
          inherit description;
        };
      };
      default = {
        foo.opt = false;
        bar.opt = true;
      };
    in
    {
      expr = slib.parseOption (evalType (lib.types.attrsOf (lib.types.submodule subModule)) default);
      expected = {
        type = "object";
        additionalProperties = {
          type = "object";
          additionalProperties = false;
          properties = {
            opt = {
              type = "boolean";
              default = true;
              inherit description;
            };
          };
        };
        inherit default description;
      };
    };

  testListOfSubmodule =
    let
      subModule = {
        options.opt = lib.mkOption {
          type = lib.types.bool;
          default = true;
          inherit description;
        };
      };
      default = [
        { opt = false; }
        { opt = true; }
      ];
    in
    {
      expr = slib.parseOption (evalType (lib.types.listOf (lib.types.submodule subModule)) default);
      expected = {
        type = "array";
        items = {
          type = "object";
          additionalProperties = false;
          properties = {
            opt = {
              type = "boolean";
              default = true;
              inherit description;
            };
          };
        };
        inherit default description;
      };
    };

  testEither =
    let
      default = "foo";
    in
    {
      expr = slib.parseOption (evalType (lib.types.either lib.types.bool lib.types.str) default);
      expected = {
        oneOf = [
          { type = "boolean"; }
          { type = "string"; }
        ];
        inherit default description;
      };
    };

  testAnything =
    let
      default = "foo";
    in
    {
      expr = slib.parseOption (evalType lib.types.anything default);
      expected = {
        inherit default description;
        type = [
          "boolean"
          "integer"
          "number"
          "string"
          "array"
          "object"
          "null"
        ];
      };
    };

  testUnspecified =
    let
      default = "foo";
    in
    {
      expr = slib.parseOption (evalType lib.types.unspecified default);
      expected = {
        inherit default description;
        type = [
          "boolean"
          "integer"
          "number"
          "string"
          "array"
          "object"
          "null"
        ];
      };
    };

  testRaw =
    let
      default = "foo";
    in
    {
      expr = slib.parseOption (evalType lib.types.raw default);
      expected = {
        inherit default description;
        type = [
          "boolean"
          "integer"
          "number"
          "string"
          "array"
          "object"
          "null"
        ];
      };
    };
}
