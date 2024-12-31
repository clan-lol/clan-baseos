{
  lib,
  config,
  pkgs,
  options,
  extendModules,
  modulesPath,
  ...
}:
let
  # Flatten the list of state folders into a single list
  stateFolders = lib.flatten (
    lib.mapAttrsToList (_item: attrs: attrs.folders) config.clan.core.state
  );

  vmModule = {
    imports = [
      (modulesPath + "/virtualisation/qemu-vm.nix")
      ./serial.nix
      ./waypipe.nix
    ];

    clan.core.state.HOME.folders = [ "/home" ];

    clan.services.waypipe = {
      inherit (config.clan.core.vm.inspect.waypipe) enable command;
    };

    # required for issuing shell commands via qga
    services.qemuGuest.enable = true;

    # required to react to system_powerdown qmp command
    # Some desktop managers like xfce override the poweroff signal and therefore
    #   make it impossible to handle it via 'logind' directly.
    services.acpid.enable = true;
    services.acpid.handlers.power.event = "button/power.*";
    services.acpid.handlers.power.action = "poweroff";

    # only works on x11
    services.spice-vdagentd.enable = config.services.xserver.enable;

    boot.initrd.systemd.enable = true;

    boot.initrd.systemd.storePaths = [
      pkgs.util-linux
      pkgs.e2fsprogs
    ];
    boot.initrd.systemd.emergencyAccess = true;

    # userborn would be faster because it doesn't need perl, but it cannot create normal users
    services.userborn.enable = true;
    users.mutableUsers = false;
    users.allowNoPasswordLogin = true;

    boot.initrd.kernelModules = [ "virtiofs" ];
    virtualisation.writableStore = false;
    virtualisation.fileSystems = lib.mkForce (
      {
        "/nix/store" = {
          device = "nix-store";
          options = [
            "x-systemd.requires=systemd-modules-load.service"
            "ro"
          ];
          fsType = "virtiofs";
        };

        "/" = {
          device = "/dev/vda";
          fsType = "ext4";
          options = [
            "defaults"
            "x-systemd.makefs"
            "nobarrier"
            "noatime"
            "nodiratime"
            "data=writeback"
            "discard"
          ];
        };

        "/vmstate" = {
          device = "/dev/vdb";
          options = [
            "x-systemd.makefs"
            "noatime"
            "nodiratime"
            "discard"
          ];
          noCheck = true;
          fsType = "ext4";
        };

        ${config.clan.core.facts.secretUploadDirectory} = {
          device = "secrets";
          fsType = "9p";
          neededForBoot = true;
          options = [
            "trans=virtio"
            "version=9p2000.L"
            "cache=loose"
          ];
        };
      }
      // lib.listToAttrs (
        map (
          folder:
          lib.nameValuePair folder {
            device = "/vmstate${folder}";
            fsType = "none";
            options = [ "bind" ];
          }
        ) stateFolders
      )
    );
  };

  # We cannot simply merge the VM config into the current system config, because
  # it is not necessarily a VM.
  # Instead we use extendModules to create a second instance of the current
  # system configuration, and then merge the VM config into that.
  vmConfig = extendModules { modules = [ vmModule ]; };
in
{
  options = {
    clan.virtualisation = {
      cores = lib.mkOption {
        type = lib.types.ints.positive;
        default = 1;
        description = ''
          Specify the number of cores the guest is permitted to use.
          The number can be higher than the available cores on the
          host system.
        '';
      };

      memorySize = lib.mkOption {
        type = lib.types.ints.positive;
        default = 1024;
        description = ''
          The memory size in megabytes of the virtual machine.
        '';
      };

      graphics = lib.mkOption {
        type = lib.types.bool;
        default = true;
        description = ''
          Whether to run QEMU with a graphics window, or in nographic mode.
          Serial console will be enabled on both settings, but this will
          change the preferred console.
        '';
      };

      waypipe = {
        enable = lib.mkOption {
          type = lib.types.bool;
          default = false;
          description = ''
            Whether to use waypipe for native wayland passthrough, or not.
          '';
        };
        command = lib.mkOption {
          type = lib.types.listOf lib.types.str;
          default = [ ];
          description = "Commands that waypipe should run";
        };
      };
    };
    # All important VM config variables needed by the vm runner
    # this is really just a remapping of values defined elsewhere
    # and therefore not intended to be set by the user
    clan.core.vm.inspect = {
      clan_name = lib.mkOption {
        type = lib.types.str;
        internal = true;
        readOnly = true;
        description = ''
          the name of the clan
        '';
      };
      memory_size = lib.mkOption {
        type = lib.types.int;
        internal = true;
        readOnly = true;
        description = ''
          the amount of memory to allocate to the vm
        '';
      };
      cores = lib.mkOption {
        type = lib.types.int;
        internal = true;
        readOnly = true;
        description = ''
          the number of cores to allocate to the vm
        '';
      };
      graphics = lib.mkOption {
        type = lib.types.bool;
        internal = true;
        readOnly = true;
        description = ''
          whether to enable graphics for the vm
        '';
      };

      waypipe = {
        enable = lib.mkOption {
          type = lib.types.bool;
          internal = true;
          readOnly = true;
          description = ''
            Whether to use waypipe for native wayland passthrough, or not.
          '';
        };
        command = lib.mkOption {
          type = lib.types.listOf lib.types.str;
          internal = true;
          readOnly = true;
          description = "Commands that waypipe should run";
        };
      };
      machine_icon = lib.mkOption {
        type = lib.types.nullOr lib.types.path;
        internal = true;
        readOnly = true;
        description = ''
          the location of the clan icon
        '';
      };
      machine_name = lib.mkOption {
        type = lib.types.str;
        internal = true;
        readOnly = true;
        description = ''
          the name of the vm
        '';
      };
      machine_description = lib.mkOption {
        type = lib.types.nullOr lib.types.str;
        internal = true;
        readOnly = true;
        description = ''
          the description of the vm
        '';
      };
    };
  };

  config = {
    # for clan vm inspect
    clan.core.vm.inspect = {
      clan_name = config.clan.core.name;
      machine_icon = config.clan.core.machineIcon or config.clan.core.icon;
      machine_name = config.clan.core.settings.machine.name;
      machine_description = config.clan.core.machineDescription;
      memory_size = config.clan.virtualisation.memorySize;
      inherit (config.clan.virtualisation) cores graphics waypipe;
    };
    # for clan vm create
    system.clan.vm = {
      create = pkgs.writeText "vm.json" (
        builtins.toJSON {
          initrd = "${vmConfig.config.system.build.initialRamdisk}/${vmConfig.config.system.boot.loader.initrdFile}";
          toplevel = vmConfig.config.system.build.toplevel;
          regInfo = (pkgs.closureInfo { rootPaths = vmConfig.config.virtualisation.additionalPaths; });
          inherit (config.clan.virtualisation)
            memorySize
            cores
            graphics
            waypipe
            ;
        }
      );
    };

    virtualisation = lib.optionalAttrs (options.virtualisation ? cores) {
      memorySize = lib.mkDefault config.clan.virtualisation.memorySize;
      graphics = lib.mkDefault config.clan.virtualisation.graphics;
      cores = lib.mkDefault config.clan.virtualisation.cores;
    };
  };
}
