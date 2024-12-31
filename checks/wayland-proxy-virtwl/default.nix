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
            clan.core.settings.machine.name = "machine";
            clan.core.settings.directory = ./.;
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
