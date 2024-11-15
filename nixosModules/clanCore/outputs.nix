{
  config,
  lib,
  pkgs,
  ...
}:
{
  # TODO: factor these out into a separate interface.nix.
  # Also think about moving these options out of `system.clan`.
  # Maybe we should not re-use the already polluted confg.system namespace
  #   and instead have a separate top-level namespace like `clanOutputs`, with
  #   well defined options marked as `internal = true;`.
  options.system.clan = lib.mkOption {
    type = lib.types.submodule {
      options = {
        deployment.data = lib.mkOption {
          type = lib.types.attrs;
          description = ''
            the data to be written to the deployment.json file
          '';
        };
        deployment.file = lib.mkOption {
          type = lib.types.path;
          description = ''
            the location of the deployment.json file
          '';
        };
        deployment.buildHost = lib.mkOption {
          type = lib.types.nullOr lib.types.str;
          description = ''
            the hostname of the build host where nixos-rebuild is run
          '';
        };
        deployment.targetHost = lib.mkOption {
          type = lib.types.nullOr lib.types.str;
          description = ''
            the hostname of the target host to be deployed to
          '';
        };
        deployment.requireExplicitUpdate = lib.mkOption {
          type = lib.types.bool;
          description = ''
            if true, the deployment will not be updated automatically.
          '';
          default = false;
        };
        deployment.nixosMobileWorkaround = lib.mkOption {
          type = lib.types.bool;
          description = ''
            if true, the deployment will first do a nixos-rebuild switch 
            to register the boot profile the command will fail applying it to the running system
            which is why afterwards we execute a nixos-rebuild test to apply 
            the new config without having to reboot. 
            This is a nixos-mobile deployment bug and will be removed in the future
          '';
          default = false;
        };
        vm.create = lib.mkOption {
          type = lib.types.path;
          description = ''
            json metadata about the vm
          '';
        };
        iso = lib.mkOption {
          type = lib.types.path;
          description = ''
            A generated iso of the machine for the flash command
          '';
        };
      };
    };
    description = ''
      utility outputs for clan management of this machine
    '';
  };
  # optimization for faster secret generate/upload and machines update
  config = {
    system.clan.deployment.data = {
      facts = {
        inherit (config.clan.core.facts)
          secretUploadDirectory
          secretModule
          publicModule
          services
          ;
      };
      sops.defaultGroups = config.clan.core.sops.defaultGroups;
      inherit (config.clan.core.networking) targetHost buildHost;
      inherit (config.system.clan.deployment) nixosMobileWorkaround;
      inherit (config.clan.deployment) requireExplicitUpdate;
    };
    system.clan.deployment.file = pkgs.writeText "deployment.json" (
      builtins.toJSON config.system.clan.deployment.data
    );
  };
}
