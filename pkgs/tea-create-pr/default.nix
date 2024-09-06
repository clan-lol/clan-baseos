{
  writeShellApplication,
  bash,
  coreutils,
  git,
  tea,
  openssh,
  # our formatter
  formatter,
}:
writeShellApplication {
  name = "tea-create-pr";
  runtimeInputs = [
    bash
    coreutils
    git
    tea
    openssh

    # our treefmt formatter wrapped with correct config
    formatter
  ];
  text = builtins.readFile ./script.sh;
}
