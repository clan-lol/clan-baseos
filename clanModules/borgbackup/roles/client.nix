{
  config,
  lib,
  pkgs,
  ...
}:
let
  # Instances might be empty, if the module is not used via the inventory
  instances = config.clan.inventory.services.borgbackup or { };
  # roles = { ${role_name} :: { machines :: [string] } }
  allServers = lib.foldlAttrs (
    acc: _instanceName: instanceConfig:
    acc
    ++ (
      if builtins.elem machineName instanceConfig.roles.client.machines then
        instanceConfig.roles.server.machines
      else
        [ ]
    )
  ) [ ] instances;

  inherit (config.clan.core) machineName;

  cfg = config.clan.borgbackup;
  preBackupScript = ''
    declare -A preCommandErrors

    ${lib.concatMapStringsSep "\n" (
      state:
      lib.optionalString (state.preBackupCommand != null) ''
        echo "Running pre-backup command for ${state.name}"
        if ! /run/current-system/sw/bin/${state.preBackupCommand}; then
          preCommandErrors["${state.name}"]=1
        fi
      ''
    ) (lib.attrValues config.clan.core.state)}

    if [[ ''${#preCommandErrors[@]} -gt 0 ]]; then
      echo "pre-backup commands failed for the following services:"
      for state in "''${!preCommandErrors[@]}"; do
        echo "  $state"
      done
      exit 1
    fi
  '';
in
{
  options.clan.borgbackup.destinations = lib.mkOption {
    type = lib.types.attrsOf (
      lib.types.submodule (
        { name, ... }:
        {
          options = {
            name = lib.mkOption {
              type = lib.types.strMatching "^[a-zA-Z0-9._-]+$";
              default = name;
              description = "the name of the backup job";
            };
            repo = lib.mkOption {
              type = lib.types.str;
              description = "the borgbackup repository to backup to";
            };
            rsh = lib.mkOption {
              type = lib.types.str;
              default = "ssh -i ${
                config.clan.core.facts.services.borgbackup.secret."borgbackup.ssh".path
              } -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o IdentitiesOnly=Yes";
              defaultText = "ssh -i \${config.clan.core.facts.services.borgbackup.secret.\"borgbackup.ssh\".path} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null";
              description = "the rsh to use for the backup";
            };
          };
        }
      )
    );
    default = { };
    description = ''
      destinations where the machine should be backuped to
    '';
  };

  options.clan.borgbackup.exclude = lib.mkOption {
    type = lib.types.listOf lib.types.str;
    example = [ "*.pyc" ];
    default = [ ];
    description = ''
      Directories/Files to exclude from the backup.
      Use * as a wildcard.
    '';
  };

  config = {

    # Destinations
    clan.borgbackup.destinations =
      let
        destinations = builtins.map (serverName: {
          name = serverName;
          value = {
            repo = "borg@${serverName}:/var/lib/borgbackup/${machineName}";
          };
        }) allServers;
      in
      (builtins.listToAttrs destinations);

    # Derived from the destinations
    systemd.services = lib.mapAttrs' (
      _: dest:
      lib.nameValuePair "borgbackup-job-${dest.name}" {
        # since borgbackup mounts the system read-only, we need to run in a ExecStartPre script, so we can generate additional files.
        serviceConfig.ExecStartPre = [
          ''+${pkgs.writeShellScript "borgbackup-job-${dest.name}-pre-backup-commands" preBackupScript}''
        ];
      }
    ) cfg.destinations;

    services.borgbackup.jobs = lib.mapAttrs (_: dest: {
      paths = lib.unique (
        lib.flatten (map (state: state.folders) (lib.attrValues config.clan.core.state))
      );
      exclude = cfg.exclude;
      repo = dest.repo;
      environment.BORG_RSH = dest.rsh;
      compression = "auto,zstd";
      startAt = "*-*-* 01:00:00";
      persistentTimer = true;

      encryption = {
        mode = "repokey";
        passCommand = "cat ${config.clan.core.facts.services.borgbackup.secret."borgbackup.repokey".path}";
      };

      prune.keep = {
        within = "1d"; # Keep all archives from the last day
        daily = 7;
        weekly = 4;
        monthly = 0;
      };
    }) cfg.destinations;

    environment.systemPackages = [
      (pkgs.writeShellScriptBin "borgbackup-create" ''
        set -efu -o pipefail
        ${lib.concatMapStringsSep "\n" (dest: ''
          systemctl start borgbackup-job-${dest.name}
        '') (lib.attrValues cfg.destinations)}
      '')
      (pkgs.writeShellScriptBin "borgbackup-list" ''
        set -efu -o pipefail
        (${
          lib.concatMapStringsSep "\n" (
            dest:
            # we need yes here to skip the changed url verification
            ''echo y | borg-job-${dest.name} list --json | jq '[.archives[] | {"name": ("${dest.name}::${dest.repo}::" + .name)}]' ''
          ) (lib.attrValues cfg.destinations)
        }) | ${pkgs.jq}/bin/jq -s 'add // []'
      '')
      (pkgs.writeShellScriptBin "borgbackup-restore" ''
        set -efu -o pipefail
        cd /
        IFS=':' read -ra FOLDER <<< "$FOLDERS"
        job_name=$(echo "$NAME" | ${pkgs.gawk}/bin/awk -F'::' '{print $1}')
        backup_name=''${NAME#"$job_name"::}
        if ! command -v borg-job-"$job_name" &> /dev/null; then
          echo "borg-job-$job_name not found: Backup name is invalid" >&2
          exit 1
        fi
        echo y | borg-job-"$job_name" extract "$backup_name" "''${FOLDER[@]}"
      '')
    ];

    # Facts generation. So the client can authenticate to the server
    clan.core.facts.services.borgbackup = {
      public."borgbackup.ssh.pub" = { };
      secret."borgbackup.ssh" = { };
      secret."borgbackup.repokey" = { };
      generator.path = [
        pkgs.openssh
        pkgs.coreutils
        pkgs.xkcdpass
      ];
      generator.script = ''
        ssh-keygen -t ed25519 -N "" -f "$secrets"/borgbackup.ssh
        mv "$secrets"/borgbackup.ssh.pub "$facts"/borgbackup.ssh.pub
        xkcdpass -n 4 -d - > "$secrets"/borgbackup.repokey
      '';
    };

    clan.core.backups.providers.borgbackup = {
      list = "borgbackup-list";
      create = "borgbackup-create";
      restore = "borgbackup-restore";
    };
  };
}
