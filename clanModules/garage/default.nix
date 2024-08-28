{ config, pkgs, ... }:
{
  systemd.services.garage.serviceConfig = {
    LoadCredential = [
      "rpc_secret_path:${config.clan.core.facts.services.garage.secret.garage_rpc_secret.path}"
      "admin_token_path:${config.clan.core.facts.services.garage.secret.garage_admin_token.path}"
      "metrics_token_path:${config.clan.core.facts.services.garage.secret.garage_metrics_token.path}"
    ];
    Environment = [
      "GARAGE_ALLOW_WORLD_READABLE_SECRETS=true"
      "GARAGE_RPC_SECRET_FILE=%d/rpc_secret_path"
      "GARAGE_ADMIN_TOKEN_FILE=%d/admin_token_path"
      "GARAGE_METRICS_TOKEN_FILE=%d/metrics_token_path"
    ];
  };

  clan.core.facts.services.garage = {
    secret.garage_rpc_secret = { };
    secret.garage_admin_token = { };
    secret.garage_metrics_token = { };
    generator.path = [
      pkgs.coreutils
      pkgs.openssl
    ];
    generator.script = ''
      openssl rand -hex -out $secrets/garage_rpc_secret 32
      openssl rand -base64 -out $secrets/garage_admin_token 32
      openssl rand -base64 -out $secrets/garage_metrics_token 32
    '';
  };

  # TODO: Vars is not in a useable state currently
  # Move back, once it is implemented.
  # clan.core.vars.generators.garage = {
  #   files.rpc_secret = { };
  #   files.admin_token = { };
  #   files.metrics_token = { };
  #   runtimeInputs = [
  #     pkgs.coreutils
  #     pkgs.openssl
  #   ];
  #   script = ''
  #     openssl rand -hex -out $out/rpc_secret 32
  #     openssl rand -base64 -out $out/admin_token 32
  #     openssl rand -base64 -out $out/metrics_token 32
  #   '';
  # };

  clan.core.state.garage.folders = [ config.services.garage.settings.metadata_dir ];
}
