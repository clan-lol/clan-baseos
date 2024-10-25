# Replace this file with an actual hardware-configuration.nix!
throw ''
  Did you forget to generate your hardware config?

  Run the following command:

  'clan machines update-hardware-config <machine_name> <hostname>'

  OR:

  'ssh root@<hostname> nixos-generate-config --no-filesystems --show-hardware-config > hardware-configuration.nix'

  And manually replace this file with the generated "hardware-configuration.nix".
''
