{
  config,
  lib,
  ...
}:
{
  imports = [
    (lib.mkRemovedOptionModule [
      "clan"
      "heisenbridge"
      "enable"
    ] "Importing the module will already enable the service.")
  ];
  config = {
    services.heisenbridge = {
      enable = true;
      homeserver = "http://localhost:8008"; # TODO: Sync with matrix-synapse
    };
    services.matrix-synapse.settings.app_service_config_files = [
      "/var/lib/heisenbridge/registration.yml"
    ];
  };
}
