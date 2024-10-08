{
  pkgs,
  lib,
  config,
  ...
}:
{
  options.clan.services.waypipe = {
    enable = lib.mkEnableOption "waypipe";
    user = lib.mkOption {
      type = lib.types.str;
      default = "user";
      description = "User the program is run under";
    };
    flags = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [
        "--vsock"
        "-s"
        "3049"
        "server"
      ];
      description = "Flags that will be passed to waypipe";
    };
    command = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ (lib.getExe pkgs.foot) ];
      description = "Commands that waypipe should run";
    };
  };
  config = lib.mkIf config.clan.services.waypipe.enable {
    # Waypipe needs pipewire
    services.pipewire = {
      enable = lib.mkDefault true;
      alsa.enable = lib.mkDefault true;
      alsa.support32Bit = lib.mkDefault true;
      pulse.enable = lib.mkDefault true;
    };
    # General default settings
    fonts.enableDefaultPackages = lib.mkDefault true;
    hardware.opengl.enable = lib.mkDefault true;

    # User account
    services.getty.autologinUser = lib.mkDefault config.clan.services.waypipe.user;
    security.sudo.wheelNeedsPassword = false;

    users.users.user = lib.mkIf (config.clan.services.waypipe.user == "user") {
      uid = 1000;
      group = "users";
      initialPassword = "";
      extraGroups = [
        "wheel"
        "video"
      ];
      home = "/home/user";
      shell = "/run/current-system/sw/bin/bash";
    };

    systemd.user.services.waypipe = {
      serviceConfig.PassEnvironment = "DISPLAY";
      serviceConfig.Environment = ''
        XDG_SESSION_TYPE=wayland \
        NIXOS_OZONE_WL=1 \
        GDK_BACKEND=wayland \
        QT_QPA_PLATFORM=wayland \
        CLUTTER_BACKEND = "wayland" \
        SDL_VIDEODRIVER=wayland
      '';
      script = ''
        ${lib.getExe pkgs.waypipe} \
        ${lib.escapeShellArgs config.clan.services.waypipe.flags} \
        ${lib.escapeShellArgs config.clan.services.waypipe.command}
      '';
      wantedBy = [ "default.target" ];
    };
  };
}
