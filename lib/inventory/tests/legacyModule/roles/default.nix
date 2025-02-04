{
  lib,
  config,
  clan-core,
  ...
}:
{
  # Just some random stuff
  config.user.user = lib.mapAttrs clan-core.users.root;
}
