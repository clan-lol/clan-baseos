{ config, lib, ... }:

{

  imports = [
    (lib.mkRemovedOptionModule [
      "clan"
      "nginx"
      "enable"
    ] "Importing the module will already enable the service.")

  ];
  options = {
    clan.nginx.acme.email = lib.mkOption {
      type = lib.types.str;
      description = ''
        Email address for account creation and correspondence from the CA.
        It is recommended to use the same email for all certs to avoid account
        creation limits.
      '';
    };
  };
  config = {
    security.acme.acceptTerms = true;
    security.acme.defaults.email = config.clan.nginx.acme.email;

    networking.firewall.allowedTCPPorts = [
      443
      80
    ];

    services.nginx = {
      enable = true;

      statusPage = lib.mkDefault true;
      recommendedBrotliSettings = lib.mkDefault true;
      recommendedGzipSettings = lib.mkDefault true;
      recommendedOptimisation = lib.mkDefault true;
      recommendedProxySettings = lib.mkDefault true;
      recommendedTlsSettings = lib.mkDefault true;
      recommendedZstdSettings = lib.mkDefault true;

      # Nginx sends all the access logs to /var/log/nginx/access.log by default.
      # instead of going to the journal!
      commonHttpConfig = "access_log syslog:server=unix:/dev/log;";

      resolver.addresses =
        let
          isIPv6 = addr: builtins.match ".*:.*:.*" addr != null;
          escapeIPv6 = addr: if isIPv6 addr then "[${addr}]" else addr;
          cloudflare = [
            "1.1.1.1"
            "2606:4700:4700::1111"
          ];
          resolvers =
            if config.networking.nameservers == [ ] then cloudflare else config.networking.nameservers;
        in
        map escapeIPv6 resolvers;

      sslDhparam = config.security.dhparams.params.nginx.path;
    };

    security.dhparams = {
      enable = true;
      params.nginx = { };
    };
  };

}
