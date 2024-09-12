{
  lib ? import <nixpkgs/lib>,
}:
let
  inherit (import ../funcs.nix { inherit lib; }) collectFiles;
in
{
  test_collectFiles = {
    expr = collectFiles {
      # secret, deployed
      generators.gen_1.files.secret_deployed_file.secret = true;
      generators.gen_1.files.secret_deployed_file.deploy = true;
      generators.gen_1.files.secret_deployed_file.share = false;

      # secret, deployed, shared
      generators.gen_1.files.secret_deployed_shared_file.secret = true;
      generators.gen_1.files.secret_deployed_shared_file.deploy = true;
      generators.gen_1.files.secret_deployed_shared_file.share = true;

      # secret, undeployed
      generators.gen_1.files.secret_undeployed_file.secret = true;
      generators.gen_1.files.secret_undeployed_file.deploy = false;
      generators.gen_1.files.secret_undeployed_file.share = false;

      # public, deployed
      generators.gen_1.files.public_deployed_file.secret = false;
      generators.gen_1.files.public_deployed_file.deploy = true;
      generators.gen_1.files.public_deployed_file.share = false;

      # secret deployed (different generator)
      generators.gen_2.files.secret_deployed_file.secret = true;
      generators.gen_2.files.secret_deployed_file.deploy = true;
      generators.gen_2.files.secret_deployed_file.share = false;
    };
    expected = [
      {
        generator = "gen_1";
        name = "secret_deployed_file";
        share = false;
      }
      {
        generator = "gen_1";
        name = "secret_deployed_shared_file";
        share = true;
      }
      {
        generator = "gen_2";
        name = "secret_deployed_file";
        share = false;
      }
    ];
  };
}
