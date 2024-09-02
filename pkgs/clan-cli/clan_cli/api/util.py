import copy
import dataclasses
import pathlib
from dataclasses import MISSING
from types import NoneType, UnionType
from typing import (
    Annotated,
    Any,
    Literal,
    TypeVar,
    Union,
    get_args,
    get_origin,
)


class JSchemaTypeError(Exception):
    pass


# Inspect the fields of the parameterized type
def inspect_dataclass_fields(t: type) -> dict[TypeVar, type]:
    """
    Returns a map of type variables to actual types for a parameterized type.
    """
    origin = get_origin(t)
    type_args = get_args(t)
    if origin is None:
        return {}

    type_params = origin.__parameters__
    # Create a map from type parameters to actual type arguments
    type_map = dict(zip(type_params, type_args, strict=False))

    return type_map


def apply_annotations(schema: dict[str, Any], annotations: list[Any]) -> dict[str, Any]:
    """
    Add metadata from typing.annotations to the json Schema.
    The annotations can be a dict, a tuple, or a string and is directly applied to the schema as shown below.
    No further validation is done, the caller is responsible for following json-schema.

    Examples

    ```python
    # String annotation
    Annotated[int, "This is an int"] -> {"type": "integer", "description": "This is an int"}

    # Dict annotation
    Annotated[int, {"minimum": 0, "maximum": 10}] -> {"type": "integer", "minimum": 0, "maximum": 10}

    # Tuple annotation
    Annotated[int, ("minimum", 0)] -> {"type": "integer", "minimum": 0}
    ```
    """
    for annotation in annotations:
        if isinstance(annotation, dict):
            # Assuming annotation is a dict that can directly apply to the schema
            schema.update(annotation)
        elif isinstance(annotation, tuple) and len(annotation) == 2:
            # Assuming a tuple where first element is a keyword (like 'minLength') and the second is the value
            schema[annotation[0]] = annotation[1]
        elif isinstance(annotation, str):
            # String annotations can be used for description
            schema.update({"description": f"{annotation}"})
    return schema


def type_to_dict(
    t: Any, scope: str = "", type_map: dict[TypeVar, type] | None = None
) -> dict:
    if type_map is None:
        type_map = {}
    if t is None:
        return {"type": "null"}

    if dataclasses.is_dataclass(t):
        fields = dataclasses.fields(t)
        properties = {
            f.metadata.get("alias", f.name): type_to_dict(
                f.type, f"{scope} {t.__name__}.{f.name}", type_map
            )
            for f in fields
            if not f.name.startswith("_")
        }

        required = set()
        for pn, pv in properties.items():
            if pv.get("type") is not None:
                if "null" not in pv["type"]:
                    required.add(pn)

            elif pv.get("oneOf") is not None:
                if "null" not in [i["type"] for i in pv.get("oneOf", [])]:
                    required.add(pn)

        required_fields = {
            f.name
            for f in fields
            if f.default is MISSING and f.default_factory is MISSING
        }

        # Find intersection
        intersection = required & required_fields

        return {
            "type": "object",
            "properties": properties,
            "required": list(intersection),
            # Dataclasses can only have the specified properties
            "additionalProperties": False,
        }

    elif type(t) is UnionType:
        return {
            "oneOf": [type_to_dict(arg, scope, type_map) for arg in t.__args__],
        }

    if isinstance(t, TypeVar):
        # if t is a TypeVar, look up the type in the type_map
        # And return the resolved type instead of the TypeVar
        resolved = type_map.get(t)
        if not resolved:
            raise JSchemaTypeError(
                f"{scope} - TypeVar {t} not found in type_map, map: {type_map}"
            )
        return type_to_dict(type_map.get(t), scope, type_map)

    elif hasattr(t, "__origin__"):  # Check if it's a generic type
        origin = get_origin(t)
        args = get_args(t)

        if origin is None:
            # Non-generic user-defined or built-in type
            # TODO: handle custom types
            raise JSchemaTypeError(f"{scope} Unhandled Type: ", origin)

        elif origin is Literal:
            # Handle Literal values for enums in JSON Schema
            return {
                "type": "string",
                "enum": list(args),  # assumes all args are strings
            }

        elif origin is Annotated:
            base_type, *metadata = get_args(t)
            schema = type_to_dict(base_type, scope)  # Generate schema for the base type
            return apply_annotations(schema, metadata)

        elif origin is Union:
            union_types = [type_to_dict(arg, scope, type_map) for arg in t.__args__]
            return {
                "oneOf": union_types,
            }

        elif origin in {list, set, frozenset}:
            return {
                "type": "array",
                "items": type_to_dict(t.__args__[0], scope, type_map),
            }

        elif issubclass(origin, dict):
            value_type = t.__args__[1]
            if value_type is Any:
                return {"type": "object", "additionalProperties": True}
            else:
                return {
                    "type": "object",
                    "additionalProperties": type_to_dict(value_type, scope, type_map),
                }
        # Generic dataclass with type parameters
        elif dataclasses.is_dataclass(origin):
            # This behavior should mimic the scoping of typeVars in dataclasses
            # Once type_to_dict() encounters a TypeVar, it will look up the type in the type_map
            # When type_to_dict() returns the map goes out of scope.
            # This behaves like a stack, where the type_map is pushed and popped as we traverse the dataclass fields
            new_map = copy.deepcopy(type_map)
            new_map.update(inspect_dataclass_fields(t))
            return type_to_dict(origin, scope, new_map)

        raise JSchemaTypeError(f"{scope} - Error api type not yet supported {t!s}")

    elif isinstance(t, type):
        if t is str:
            return {"type": "string"}
        if t is int:
            return {"type": "integer"}
        if t is float:
            return {"type": "number"}
        if t is bool:
            return {"type": "boolean"}
        if t is object:
            return {"type": "object"}
        if t is Any:
            raise JSchemaTypeError(
                f"{scope} - Usage of the Any type is not supported for API functions. In: {scope}"
            )
        if t is pathlib.Path:
            return {
                # TODO: maybe give it a pattern for URI
                "type": "string",
            }
        if t is dict:
            raise JSchemaTypeError(
                f"{scope} - Generic 'dict' type not supported. Use dict[str, Any] or any more expressive type."
            )

        # Optional[T] gets internally transformed Union[T,NoneType]
        if t is NoneType:
            return {"type": "null"}

        raise JSchemaTypeError(f"{scope} - Error primitive type not supported {t!s}")
    else:
        raise JSchemaTypeError(f"{scope} - Error type not supported {t!s}")
