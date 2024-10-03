{
  config,
  pkgs,
  ...
}:

{

  config = {
    clan.core.vars.generators.disk-id = {
      files.diskId.secret = false;
      runtimeInputs = [
        pkgs.coreutils
        pkgs.bash
      ];
      script = ''
        uuid=$(bash ${../../uuid4.sh})

        # Remove the hyphens from the UUID
        uuid_no_hyphens=$(echo -n "$uuid" | tr -d '-')

        echo -n "$uuid_no_hyphens" > "$out/diskId"
      '';
    };
  };
}
