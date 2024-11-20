{
  lib,
  config,
  pkgs,
  ...
}:
let
  inherit (lib) mkOption;
  inherit (builtins)
    hashString
    toJSON
    ;
  inherit (lib.types)
    attrsOf
    bool
    either
    enum
    int
    listOf
    nullOr
    oneOf
    package
    path
    str
    submoduleWith
    ;
  # the original types.submodule has strange behavior
  submodule =
    module:
    submoduleWith {
      specialArgs.pkgs = pkgs;
      modules = [ module ];
    };
in
{
  options = {
    settings = import ./settings-opts.nix { inherit lib; };
    generators = lib.mkOption {
      description = ''
        A set of generators that can be used to generate files.
        Generators are scripts that produce files based on the values of other generators and user input.
        Each generator is expected to produce a set of files under a directory.
      '';
      default = { };
      type = attrsOf (
        submodule (generator: {
          imports = [ ./generator.nix ];
          options = {
            dependencies = lib.mkOption {
              description = ''
                A list of other generators that this generator depends on.
                The output values of these generators will be available to the generator script as files.
                For example, the file 'file1' of a dependency named 'dep1' will be available via $in/dep1/file1.
              '';
              type = listOf str;
              default = [ ];
            };
            migrateFact = lib.mkOption {
              description = ''
                The fact service name to import the files from.

                Use this to migrate legacy facts to the new vars system.
              '';
              type = nullOr str;
              example = "my_service";
              default = null;
            };
            invalidationData = lib.mkOption {
              description = ''
                A set of values that invalidate the generated values.
                If any of these values change, the generated values will be re-generated.
              '';
              default = null;
              type =
                let
                  data = nullOr (oneOf [
                    bool
                    int
                    str
                    (attrsOf data)
                    # lists are not allowed as of now due to potential ordering issues
                  ]);
                in
                data;
            };
            # the invalidationHash is the validation interface to the outside world
            invalidationHash = lib.mkOption {
              internal = true;
              description = ''
                A hash of the invalidation data.
                If the hash changes, the generated values will be re-generated.
              '';
              type = nullOr str;
              # TODO: recursively traverse the structure and sort all lists in order to support lists
              default =
                # For backwards compat, the hash is null by default in which case the check is omitted
                if generator.config.invalidationData == null then
                  null
                else
                  hashString "sha256" (toJSON generator.config.invalidationData);
            };
            files = lib.mkOption {
              description = ''
                A set of files to generate.
                The generator 'script' is expected to produce exactly these files under $out.
              '';
              type = attrsOf (
                submodule (file: {
                  imports = [
                    config.settings.fileModule
                    (lib.mkRenamedOptionModule
                      [
                        "sops"
                        "owner"
                      ]
                      [
                        "owner"
                      ]
                    )
                    (lib.mkRenamedOptionModule
                      [
                        "sops"
                        "group"
                      ]
                      [
                        "group"
                      ]
                    )
                  ];
                  options = {
                    name = lib.mkOption {
                      type = lib.types.str;
                      description = ''
                        name of the public fact
                      '';
                      readOnly = true;
                      default = file.config._module.args.name;
                    };
                    generatorName = lib.mkOption {
                      type = lib.types.str;
                      description = ''
                        name of the generator
                      '';
                      readOnly = true;
                      default = generator.config._module.args.name;
                    };
                    share = lib.mkOption {
                      type = lib.types.bool;
                      description = ''
                        Whether the generated vars should be shared between machines.
                        Shared vars are only generated once, when the first machine using it is deployed.
                        Subsequent machines will re-use the already generated values.
                      '';
                      readOnly = true;
                      internal = true;
                      default = generator.config.share;
                    };
                    deploy = lib.mkOption {
                      description = ''
                        Whether the file should be deployed to the target machine.

                        Enable this if the generated file is only used as an input to other generators.
                      '';
                      type = bool;
                      default = true;
                    };
                    secret = lib.mkOption {
                      description = ''
                        Whether the file should be treated as a secret.
                      '';
                      type = bool;
                      default = true;
                    };
                    path = lib.mkOption {
                      description = ''
                        The path to the file containing the content of the generated value.
                        This will be set automatically
                      '';
                      type = str;
                    };
                    owner = lib.mkOption {
                      description = "The user name or id that will own the secret file.";
                      default = "root";
                    };
                    group = lib.mkOption {
                      description = "The group name or id that will own the secret file.";
                      default = "root";
                    };
                    value =
                      lib.mkOption {
                        description = ''
                          The content of the generated value.
                          Only available if the file is not secret.
                        '';
                        type = str;
                        defaultText = "Throws error because the value of a secret file is not accessible";
                      }
                      // lib.optionalAttrs file.config.secret {
                        default = throw "Cannot access value of secret file";
                      };
                  };
                })
              );
            };
            prompts = lib.mkOption {
              description = ''
                A set of prompts to ask the user for values.
                Prompts are available to the generator script as files.
                For example, a prompt named 'prompt1' will be available via $prompts/prompt1
              '';
              default = { };
              type = attrsOf (
                submodule (prompt: {
                  options = {
                    createFile = lib.mkOption {
                      description = ''
                        Whether the prompted value should be stored in a file with the same name as the prompt.

                        If enabled, the behavior is equivalent to the following configuration:
                        ```nix
                        {
                          files.<name>.secret = true;
                          script = "cp $prompts/<name> $out/<name>";
                        }
                        ```
                      '';
                      type = bool;
                      default = true;
                    };
                    description = lib.mkOption {
                      description = ''
                        The description of the prompted value
                      '';
                      type = str;
                      example = "SSH private key";
                      default = prompt.config._module.args.name;
                    };
                    type = lib.mkOption {
                      description = ''
                        The input type of the prompt.
                        The following types are available:
                          - hidden: A hidden text (e.g. password)
                          - line: A single line of text
                          - multiline: A multiline text
                      '';
                      type = enum [
                        "hidden"
                        "line"
                        "multiline"
                      ];
                      default = "line";
                    };
                  };
                })
              );
            };
            runtimeInputs = lib.mkOption {
              description = ''
                A list of packages that the generator script requires.
                These packages will be available in the PATH when the script is run.
              '';
              type = listOf package;
              default = [ ];
            };
            script = lib.mkOption {
              description = ''
                The script to run to generate the files.
                The script will be run with the following environment variables:
                  - $in: The directory containing the output values of all declared dependencies
                  - $out: The output directory to put the generated files
                  - $prompts: The directory containing the prompted values as files
                The script should produce the files specified in the 'files' attribute under $out.
              '';
              type = either str path;
              default = "";
            };
            finalScript = lib.mkOption {
              description = ''
                The final generator script, wrapped, so:
                  - all required programs are in PATH
                  - sandbox is set up correctly
              '';
              type = lib.types.str;
              readOnly = true;
              internal = true;
              visible = false;
            };
            share = lib.mkOption {
              description = ''
                Whether the generated vars should be shared between machines.
                Shared vars are only generated once, when the first machine using it is deployed.
                Subsequent machines will re-use the already generated values.
              '';
              type = bool;
              default = false;
            };
          };
        })
      );
    };
  };
}
