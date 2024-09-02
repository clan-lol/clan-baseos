# ruff: noqa: RUF001
import argparse
import json
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Any


# Function to map JSON schemas and types to Python types
def map_json_type(
    json_type: Any, nested_types: set[str] | None = None, parent: Any = None
) -> set[str]:
    if nested_types is None:
        nested_types = {"Any"}
    if isinstance(json_type, list):
        res = set()
        for t in json_type:
            res |= map_json_type(t)
        return res
    if isinstance(json_type, dict):
        return map_json_type(json_type.get("type"))
    if json_type == "string":
        return {"str"}
    if json_type == "integer":
        return {"int"}
    if json_type == "boolean":
        return {"bool"}
    if json_type == "array":
        assert nested_types, f"Array type not found for {parent}"
        return {f"""list[{" | ".join(nested_types)}]"""}
    if json_type == "object":
        assert nested_types, f"dict type not found for {parent}"
        return {f"""dict[str, {" | ".join(nested_types)}]"""}
    if json_type == "null":
        return {"None"}
    msg = f"Python type not found for {json_type}"
    raise ValueError(msg)


known_classes = set()
root_class = "Inventory"


def field_def_from_default_type(
    field_name: str,
    field_types: set[str],
    class_name: str,
    finalize_field: Callable[..., str],
) -> str | None:
    if "dict" in str(field_types):
        return finalize_field(
            field_types=field_types,
            default_factory="dict",
        )

    if "list" in str(field_types):
        return finalize_field(
            field_types=field_types,
            default_factory="list",
        )
    if "None" in str(field_types):
        return finalize_field(
            field_types=field_types,
            default="None",
        )

    if class_name.endswith("Config"):
        # SingleDiskConfig
        # PackagesConfig
        # ...
        # Config classes MUST always be optional
        msg = f"""
            #################################################
            Clan module '{class_name}' specifies a top-level option '{field_name}' without a default value.

            To fix this:
            - Add a default value to the option

            lib.mkOption {{
                type = lib.types.nullOr lib.types.str;
                default = null; # <- Add a default value here
            }};

            # Other options

            - make the field nullable

            lib.mkOption {{
                #      ╔══════════════╗ <- Nullable type
                type = lib.types.nullOr lib.types.str;
            }};

            - Use lib.types.attrsOf if suitable
            - Use lib.types.listOf if suitable


            Or report this problem to the clan team. So the class generator can be improved.
            #################################################
            """
        raise ValueError(msg)

    return None


def field_def_from_default_value(
    default_value: Any,
    field_name: str,
    field_types: set[str],
    nested_class_name: str,
    finalize_field: Callable[..., str],
) -> str | None:
    # default_value = prop_info.get("default")
    if default_value is None:
        return finalize_field(
            field_types=field_types | {"None"},
            default="None",
        )
    if isinstance(default_value, list):
        return finalize_field(
            field_types=field_types,
            default_factory="list",
        )
    if isinstance(default_value, dict):
        serialised_types = " | ".join(field_types)
        if serialised_types == nested_class_name:
            return finalize_field(
                field_types=field_types,
                default_factory=nested_class_name,
            )

        if "dict[str," in serialised_types:
            return finalize_field(
                field_types=field_types,
                default_factory="dict",
            )
        return finalize_field(
            field_types=field_types,
            default_factory="dict",
            type_apendix=" | dict[str,Any]",
        )
    if default_value == "‹name›":
        return None
    if isinstance(default_value, str):
        return finalize_field(
            field_types=field_types,
            default=f"'{default_value}'",
        )
    # Other default values unhandled yet.
    msg = f"Unhandled default value for field '{field_name}' - default value: {default_value}"
    raise ValueError(msg)


def get_field_def(
    field_name: str,
    field_meta: str | None,
    field_types: set[str],
    default: str | None = None,
    default_factory: str | None = None,
    type_apendix: str = "",
) -> str:
    sorted_field_types = sorted(field_types)
    serialised_types = " | ".join(sorted_field_types) + type_apendix
    if not default and not default_factory and not field_meta:
        return f"{field_name}: {serialised_types}"
    field_init = "field("

    init_args = []
    if default:
        init_args.append(f"default = {default}")
    if default_factory:
        init_args.append(f"default_factory = {default_factory}")
    if field_meta:
        init_args.append(f"metadata = {field_meta}")

    field_init += ", ".join(init_args) + ")"

    return f"{field_name}: {serialised_types} = {field_init}"


# Recursive function to generate dataclasses from JSON schema
def generate_dataclass(schema: dict[str, Any], class_name: str = root_class) -> str:
    properties = schema.get("properties", {})

    required_fields = []
    fields_with_default = []
    nested_classes = []

    for prop, prop_info in properties.items():
        field_name = prop.replace("-", "_")

        prop_type = prop_info.get("type", None)
        union_variants = prop_info.get("oneOf", [])
        # Collect all types
        field_types = set()

        title = prop_info.get("title", prop.removesuffix("s"))
        title_sanitized = "".join([p.capitalize() for p in title.split("-")])
        nested_class_name = f"""{class_name if class_name != root_class and not prop_info.get("title") else ""}{title_sanitized}"""

        if (prop_type is None) and (not union_variants):
            msg = f"Type not found for property {prop} {prop_info}"
            raise ValueError(msg)

        if union_variants:
            field_types = map_json_type(union_variants)

        elif prop_type == "array":
            item_schema = prop_info.get("items")

            if isinstance(item_schema, dict):
                field_types = map_json_type(
                    prop_type, map_json_type(item_schema), field_name
                )

        elif prop_type == "object":
            inner_type = prop_info.get("additionalProperties")
            if inner_type and inner_type.get("type") == "object":
                # Inner type is a class
                field_types = map_json_type(prop_type, {nested_class_name}, field_name)

                #
                if nested_class_name not in known_classes:
                    nested_classes.append(
                        generate_dataclass(inner_type, nested_class_name)
                    )
                    known_classes.add(nested_class_name)

            elif inner_type and inner_type.get("type") != "object":
                # Trivial type:
                # dict[str, inner_type]
                field_types = {
                    f"""dict[str, {" | ".join(map_json_type(inner_type))}]"""
                }

            elif not inner_type:
                # The type is a class
                field_types = {nested_class_name}
                if nested_class_name not in known_classes:
                    nested_classes.append(
                        generate_dataclass(prop_info, nested_class_name)
                    )
                    known_classes.add(nested_class_name)
        else:
            field_types = map_json_type(
                prop_type,
                nested_types=set(),
                parent=field_name,
            )

        assert field_types, f"Python type not found for {prop} {prop_info}"

        field_meta = None
        if field_name != prop:
            field_meta = f"""{{"alias": "{prop}"}}"""

        finalize_field = partial(get_field_def, field_name, field_meta)

        if "default" in prop_info or field_name not in prop_info.get("required", []):
            if "default" in prop_info:
                default_value = prop_info.get("default")
                field_def = field_def_from_default_value(
                    default_value=default_value,
                    field_name=field_name,
                    field_types=field_types,
                    nested_class_name=nested_class_name,
                    finalize_field=finalize_field,
                )
                if field_def:
                    fields_with_default.append(field_def)

                if not field_def:
                    # Finalize without the default value
                    field_def = finalize_field(
                        field_types=field_types,
                    )
                    required_fields.append(field_def)

            if "default" not in prop_info:
                # Field is not required and but also specifies no default value
                # Trying to infer default value from type
                field_def = field_def_from_default_type(
                    field_name=field_name,
                    field_types=field_types,
                    class_name=class_name,
                    finalize_field=finalize_field,
                )

                if field_def:
                    fields_with_default.append(field_def)
                if not field_def:
                    field_def = finalize_field(
                        field_types=field_types,
                    )
                    required_fields.append(field_def)

        else:
            field_def = finalize_field(
                field_types=field_types,
            )
            required_fields.append(field_def)

    fields_str = "\n    ".join(required_fields + fields_with_default)
    nested_classes_str = "\n\n".join(nested_classes)

    class_def = f"@dataclass\nclass {class_name}:\n    {fields_str}\n"
    return f"{nested_classes_str}\n\n{class_def}" if nested_classes_str else class_def


def run_gen(args: argparse.Namespace) -> None:
    print(f"Converting {args.input} to {args.output}")
    dataclass_code = ""
    with args.input.open() as f:
        schema = json.load(f)
        dataclass_code = generate_dataclass(schema)

    with args.output.open("w") as f:
        f.write(
            """# DON NOT EDIT THIS FILE MANUALLY. IT IS GENERATED.
#
# ruff: noqa: N815
# ruff: noqa: N806
# ruff: noqa: F401
# fmt: off
from dataclasses import dataclass, field
from typing import Any\n\n
"""
        )
        f.write(dataclass_code)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Input JSON schema file", type=Path)
    parser.add_argument("output", help="Output Python file", type=Path)
    parser.set_defaults(func=run_gen)

    args = parser.parse_args()

    args.func(args)


if __name__ == "__main__":
    main()
