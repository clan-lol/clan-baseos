(import ../lib/container-test.nix) (
  { ... }:
  {
    name = "secrets";

    nodes.machine =
      { ... }:
      {
        networking.hostName = "machine";
        services.openssh.enable = true;
        services.openssh.startWhenNeeded = false;
      };
    testScript = ''
      start_all()
      machine.succeed("systemctl status sshd")
      machine.wait_for_unit("sshd")
    '';
  }
)
