_: {
  perSystem =
    {
      pkgs,
      ...
    }:
    {
      formatter = pkgs.nixfmt;
    };
}
