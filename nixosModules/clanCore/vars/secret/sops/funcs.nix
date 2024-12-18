{
  lib ? import <nixpkgs/lib>,
  ...
}:
let

  inherit (lib)
    filterAttrs
    flatten
    flip
    mapAttrsToList
    ;
in
{

  collectFiles =
    vars:
    let
      relevantFiles =
        generator:
        flip filterAttrs generator.files (_name: f: f.secret && f.deploy && (f.neededFor != "activation"));
      allFiles = flatten (
        flip mapAttrsToList vars.generators (
          gen_name: generator:
          flip mapAttrsToList (relevantFiles generator) (
            fname: file: {
              name = fname;
              generator = gen_name;
              neededForUsers = file.neededFor == "users";
              inherit (generator) share;
              inherit (file) owner group;
            }
          )
        )
      );
    in
    allFiles;
}
