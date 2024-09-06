import ../lib/test-base.nix (
  {
    config,
    pkgs,
    lib,
    ...
  }:
  {
    name = "wayland-proxy-virtwl";

    nodes.machine =
      { self, ... }:
      {
        imports = [
          self.nixosModules.clanCore
          {
            clan.core.machineName = "machine";
            clan.core.clanDir = ./.;
            clan.core.machine = {
              id = "df97124f09da48e3a22d77ce30ee8da6";
              diskId = "c9c52c";
            };
          }
        ];
        services.wayland-proxy-virtwl.enable = true;

        virtualisation.qemu.options = [
          "-vga none -device virtio-gpu-rutabaga,cross-domain=on,hostmem=4G,wsi=headless"
        ];

        virtualisation.qemu.package = lib.mkForce pkgs.qemu_kvm;
      };
    testScript = ''
      start_all()
      # use machinectl
      machine.succeed("machinectl shell .host ${config.nodes.machine.systemd.package}/bin/systemctl --user start wayland-proxy-virtwl >&2")
    '';
  }
)
