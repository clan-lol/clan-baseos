{ lib, ... }:
let
  inherit (lib) types mkOption;
  submodule = m: types.submoduleWith { modules = [ m ]; };

in
{
  options = {
    directory = mkOption {
      type = types.path;
    };
    inventory = mkOption {
      type = types.raw;
    };
    machines = mkOption {
      type = types.attrsOf (
        submodule (
          { name, ... }:
          let
            machineName = name;
          in
          {
            options = {
              compiledMachine = mkOption {
                type = types.raw;
              };
              compiledServices = mkOption {
                # type = types.attrsOf;
                type = types.attrsOf (
                  types.submoduleWith {
                    modules = [
                      (
                        { name, ... }:
                        let
                          serviceName = name;
                        in
                        {
                          options = {
                            machineName = mkOption {
                              default = machineName;
                              readOnly = true;
                            };
                            serviceName = mkOption {
                              default = serviceName;
                              readOnly = true;
                            };
                            # Outputs
                            machineImports = mkOption {
                              type = types.listOf types.raw;
                            };
                            supportedRoles = mkOption {
                              type = types.listOf types.str;
                            };
                            matchedRoles = mkOption {
                              type = types.listOf types.str;
                            };
                            isClanModule = mkOption {
                              type = types.bool;
                            };
                            machinesRoles = mkOption {
                              type = types.attrsOf (types.listOf types.str);
                            };
                            resolvedRolesPerInstance = mkOption {
                              type = types.attrsOf (
                                types.attrsOf (submodule {
                                  options.machines = mkOption {
                                    type = types.listOf types.str;
                                  };
                                })
                              );
                            };
                            assertions = mkOption {
                              type = types.attrsOf types.raw;
                            };
                          };
                        }
                      )
                    ];
                  }
                );
              };
              machineImports = mkOption {
                type = types.listOf types.raw;
              };
            };
          }
        )
      );
    };
  };
}
