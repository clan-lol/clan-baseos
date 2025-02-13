{ modulesPath, ... }:
{
  imports = [
    # we need these 2 modules always to be able to run the tests
    (modulesPath + "/testing/test-instrumentation.nix")
    (modulesPath + "/virtualisation/qemu-vm.nix")

    (modulesPath + "/profiles/minimal.nix")
  ];

  clan.core.setDefaults = false;
}
