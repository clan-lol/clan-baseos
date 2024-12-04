# tests for the nixos options to jsonschema converter
# run these tests via `nix-unit ./test.nix`
{
  lib ? (import <nixpkgs> { }).lib,
  slib ? (import ./. { inherit lib; }),
}:
let
  eval =
    modules:
    let
      evaledConfig = lib.evalModules {
        inherit modules;
      };
    in
    evaledConfig;
in
{
  test_default = {
    expr = slib.getPrios {
      options =
        (eval [
          {
            options.foo.bar = lib.mkOption {
              type = lib.types.bool;
              description = "Test Description";
              default = true;
            };
          }
        ]).options;
    };
    expected = {
      foo.bar = {
        __prio = 1500;
      };
    };
  };
  test_no_default = {
    expr = slib.getPrios {
      options =
        (eval [
          {
            options.foo.bar = lib.mkOption {
              type = lib.types.bool;
            };
          }
        ]).options;
    };
    expected = {
      foo.bar = {
        __prio = 9999;
      };
    };
  };

  test_submodule = {
    expr = slib.getPrios {
      options =
        (eval [
          {
            options.foo = lib.mkOption {
              type = lib.types.submodule {
                options = {
                  bar = lib.mkOption {
                    type = lib.types.bool;
                  };
                };
              };
            };
          }
        ]).options;
    };
    expected = {
      foo = {
        # Prio of the submodule itself
        __prio = 9999;

        # Prio of the bar option within the submodule
        bar.__prio = 9999;
      };
    };
  };

  # TODO(@hsjobeki): Cover this edge case
  # test_freeform =
  #   let
  #     evaluated = (
  #       eval [
  #         {
  #           freeformType = with lib.types; attrsOf (int);
  #           options = {
  #             foo = lib.mkOption {
  #               type = lib.types.int;
  #               default = 0;
  #             };
  #           };
  #         }
  #         {
  #           bar = lib.mkForce 123;
  #           baz = 1;
  #         }
  #         {
  #           bar = 10;
  #         }
  #       ]
  #     );
  #   in
  #   {
  #     inherit evaluated;
  #     expr = slib.getPrios {
  #       options = evaluated.options;
  #     };
  #     expected = {
  #     };
  #   };

  test_attrsOf_submodule =
    let
      evaluated = eval [
        {
          options.foo = lib.mkOption {
            type = lib.types.attrsOf (
              lib.types.submodule {
                options = {
                  bar = lib.mkOption {
                    type = lib.types.int;
                    default = 0;
                  };
                };
              }
            );
          };
          config.foo = {
            "nested" = {
              "bar" = 2; # <- 100 prio ?
            };
            "other" = {
              "bar" = lib.mkForce 2; # <- 50 prio ?
            };
          };
        }
      ];
    in
    {
      expr = slib.getPrios { options = evaluated.options; };
      expected = {
        foo.__prio = 100;

        foo.nested.__prio = 100;
        foo.other.__prio = 100;

        foo.nested.bar.__prio = 100;
        foo.other.bar.__prio = 50;
      };
    };
  test_attrsOf_attrsOf_submodule =
    let
      evaluated = eval [
        {
          options.foo = lib.mkOption {
            type = lib.types.attrsOf (
              lib.types.attrsOf (
                lib.types.submodule {
                  options = {
                    bar = lib.mkOption {
                      type = lib.types.int;
                      default = 0;
                    };
                  };
                }
              )
            );
          };
          config.foo = {
            a.b = {
              bar = 1;
            };
            a.c = {
              bar = 1;
            };
            x.y = {
              bar = 1;
            };
            x.z = {
              bar = 1;
            };
          };
        }
      ];
    in
    {
      inherit evaluated;
      expr = slib.getPrios { options = evaluated.options; };
      expected = {
        foo.__prio = 100;

        # Sub A
        foo.a.__prio = 100;
        # a.b doesnt have a prio
        # a.c doesnt have a prio
        foo.a.b.bar.__prio = 100;
        foo.a.c.bar.__prio = 100;

        # Sub X
        foo.x.__prio = 100;
        # x.y doesnt have a prio
        # x.z doesnt have a prio
        foo.x.y.bar.__prio = 100;
        foo.x.z.bar.__prio = 100;
      };
    };
}
