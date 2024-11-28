{ lib, ... }:
{
  secretStore = lib.mkOption {
    type = lib.types.enum [
      "sops"
      "password-store"
      "vm"
      "custom"
    ];
    default = "sops";
    description = ''
      method to store secret facts
      custom can be used to define a custom secret var store.
    '';
  };

  secretModule = lib.mkOption {
    type = lib.types.str;
    internal = true;
    description = ''
      the python import path to the secret module
    '';
  };

  # TODO: see if this is the right approach. Maybe revert to secretPathFunction
  fileModule = lib.mkOption {
    type = lib.types.deferredModule;
    internal = true;
    description = ''
      A module to be imported in every vars.files.<name> submodule.
      Used by backends to define the `path` attribute.
    '';
    default = { };
  };

  publicStore = lib.mkOption {
    type = lib.types.enum [
      "in_repo"
      "vm"
      "custom"
    ];
    default = "in_repo";
    description = ''
      method to store public vars.
      custom can be used to define a custom public vars store.
    '';
  };

  publicModule = lib.mkOption {
    type = lib.types.str;
    internal = true;
    description = ''
      the python import path to the public module
    '';
  };
}
