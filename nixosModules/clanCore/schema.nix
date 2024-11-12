{ options, lib, ... }:
let
  jsonschema = import ../../lib/jsonschema { inherit lib; } { };
in
{
  options.clanSchema = lib.mkOption {
    type = lib.types.attrs;
    description = "The json schema for the .clan options namespace";
    default = jsonschema.parseOptions options.clan { };
    defaultText = lib.literalExpression "jsonschema.schemaToJSON options.clan";
  };
}
