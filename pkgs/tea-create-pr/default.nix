{
  writeShellApplication,
  bash,
  coreutils,
  git,
  tea,
  openssh,
}:
writeShellApplication {
  name = "tea-create-pr";
  runtimeInputs = [
    bash
    coreutils
    git
    tea
    openssh
  ];
  text = builtins.readFile ./script.sh;
}
