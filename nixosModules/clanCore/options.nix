{
  lib,
  ...
}:
{
  imports = [
    (lib.mkRenamedOptionModule [ "clanCore" ] [
      "clan"
      "core"
    ])
  ];
}
