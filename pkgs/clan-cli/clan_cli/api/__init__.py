import logging
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from inspect import Parameter, Signature, signature
from typing import (
    Annotated,
    Any,
    Generic,
    Literal,
    TypeVar,
    get_type_hints,
)

log = logging.getLogger(__name__)

from .serde import dataclass_to_dict, from_dict, sanitize_string

__all__ = ["dataclass_to_dict", "from_dict", "sanitize_string"]

from clan_cli.errors import ClanError

T = TypeVar("T")

ResponseDataType = TypeVar("ResponseDataType")


@dataclass
class ApiError:
    message: str
    description: str | None
    location: list[str] | None


@dataclass
class SuccessDataClass(Generic[ResponseDataType]):
    op_key: str
    status: Annotated[Literal["success"], "The status of the response."]
    data: ResponseDataType


@dataclass
class ErrorDataClass:
    op_key: str
    status: Literal["error"]
    errors: list[ApiError]


ApiResponse = SuccessDataClass[ResponseDataType] | ErrorDataClass


def update_wrapper_signature(wrapper: Callable, wrapped: Callable) -> None:
    sig = signature(wrapped)
    params = list(sig.parameters.values())

    # Add 'op_key' parameter
    op_key_param = Parameter("op_key", 
                             Parameter.KEYWORD_ONLY, 
                             # we add a None default value so that typescript code gen drops the parameter
                             # FIXME: this is a hack, we should filter out op_key in the typescript code gen
                             default=None, 
                            annotation=str)
    params.append(op_key_param)

    # Create a new signature
    new_sig = sig.replace(parameters=params)
    wrapper.__signature__ = new_sig  # type: ignore


class MethodRegistry:
    def __init__(self) -> None:
        self._orig_signature: dict[str, Signature] = {}
        self._registry: dict[str, Callable[..., Any]] = {}

    @property
    def orig_signatures(self) -> dict[str, Signature]:
        return self._orig_signature

    @property
    def signatures(self) -> dict[str, Signature]:
        return {name: signature(fn) for name, fn in self.functions.items()}

    @property
    def functions(self) -> dict[str, Callable[..., Any]]:
        return self._registry

    def reset(self) -> None:
        self._orig_signature.clear()
        self._registry.clear()

    def register_abstract(self, fn: Callable[..., T]) -> Callable[..., T]:
        @wraps(fn)
        def wrapper(*args: Any, op_key: str, **kwargs: Any) -> ApiResponse[T]:
            msg = f"""{fn.__name__} - The platform didn't implement this function.

---
# Example

The function 'open_file()' depends on the platform.

def open_file(file_request: FileRequest) -> str | None:
    # In GTK we open a file dialog window
    # In Android we open a file picker dialog
    # and so on.
    pass

# At runtime the clan-app must override platform specific functions
API.register(open_file)
---
                """
            raise NotImplementedError(msg)

        self.register(wrapper)
        return fn

    def overwrite_fn(self, fn: Callable[..., Any]) -> None:
        fn_name = fn.__name__

        if fn_name not in self._registry:
            msg = f"Function '{fn_name}' is not registered as an API method"
            raise ClanError(msg)

        fn_signature = signature(fn)
        abstract_signature = signature(self._registry[fn_name])

        # Remove the default argument of op_key from abstract_signature
        # FIXME: This is a hack to make the signature comparison work
        # because the other hack above where default value of op_key is None in the wrapper
        abstract_params = list(abstract_signature.parameters.values())
        for i, param in enumerate(abstract_params):
            if param.name == "op_key":
                abstract_params[i] = param.replace(default=Parameter.empty)
                break
        abstract_signature = abstract_signature.replace(parameters=abstract_params)

        if fn_signature != abstract_signature:
            msg = f"Expected signature: {abstract_signature}\nActual signature: {fn_signature}"
            raise ClanError(msg)

        self._registry[fn_name] = fn

    F = TypeVar("F", bound=Callable[..., Any])

    def register(self, fn: F) -> F:
        if fn.__name__ in self._registry:
            msg = f"Function {fn.__name__} already registered"
            raise ClanError(msg)
        if fn.__name__ in self._orig_signature:
            msg = f"Function {fn.__name__} already registered"
            raise ClanError(msg)
        # make copy of original function
        self._orig_signature[fn.__name__] = signature(fn)

        @wraps(fn)
        def wrapper(*args: Any, op_key: str, **kwargs: Any) -> ApiResponse[T]:
            try:
                data: T = fn(*args, **kwargs)
                return SuccessDataClass(status="success", data=data, op_key=op_key)
            except ClanError as e:
                log.exception(f"Error calling wrapped {fn.__name__}")
                return ErrorDataClass(
                    op_key=op_key,
                    status="error",
                    errors=[
                        ApiError(
                            message=e.msg,
                            description=e.description,
                            location=[fn.__name__, e.location],
                        )
                    ],
                )
            except Exception as e:
                log.exception(f"Error calling wrapped {fn.__name__}")
                return ErrorDataClass(
                    op_key=op_key,
                    status="error",
                    errors=[
                        ApiError(
                            message=str(e),
                            description="An unexpected error occurred",
                            location=[fn.__name__],
                        )
                    ],
                )

        # @wraps preserves all metadata of fn
        # we need to update the annotation, because our wrapper changes the return type
        # This overrides the new return type annotation with the generic typeVar filled in
        orig_return_type = get_type_hints(fn).get("return")
        wrapper.__annotations__["return"] = ApiResponse[orig_return_type]  # type: ignore

        # Add additional argument for the operation key
        wrapper.__annotations__["op_key"] = str  # type: ignore

        update_wrapper_signature(wrapper, fn)

        self._registry[fn.__name__] = wrapper

        return fn

    def to_json_schema(self) -> dict[str, Any]:
        from typing import get_type_hints

        from .util import type_to_dict

        api_schema: dict[str, Any] = {
            "$comment": "An object containing API methods. ",
            "type": "object",
            "additionalProperties": False,
            "required": list(self._registry.keys()),
            "properties": {},
        }

        err_type = None
        for name, func in self._registry.items():
            hints = get_type_hints(func)

            serialized_hints = {
                key: type_to_dict(
                    value, scope=name + " argument" if key != "return" else "return"
                )
                for key, value in hints.items()
            }

            return_type = serialized_hints.pop("return")

            if err_type is None:
                err_type = next(
                    t
                    for t in return_type["oneOf"]
                    if ("error" in t["properties"]["status"]["enum"])
                )

            return_type["oneOf"][1] = {"$ref": "#/$defs/error"}

            sig = signature(func)
            required_args = []
            for n, param in sig.parameters.items():
                if param.default == Parameter.empty:
                    required_args.append(n)

            api_schema["properties"][name] = {
                "type": "object",
                "required": ["arguments", "return"],
                "additionalProperties": False,
                "properties": {
                    "return": return_type,
                    "arguments": {
                        "type": "object",
                        "required": required_args,
                        "additionalProperties": False,
                        "properties": serialized_hints,
                    },
                },
            }

        api_schema["$defs"] = {"error": err_type}

        return api_schema

    def get_method_argtype(self, method_name: str, arg_name: str) -> Any:
        from inspect import signature

        func = self._registry.get(method_name, None)
        if not func:
            msg = f"API Method {method_name} not found in registry. Available methods: {list(self._registry.keys())}"
            raise ClanError(msg)

        sig = signature(func)

        # seems direct 'key in dict' doesnt work here
        if arg_name not in sig.parameters.keys():  # noqa: SIM118
            msg = f"Argument {arg_name} not found in api method '{method_name}'. Avilable arguments: {list(sig.parameters.keys())}"
            raise ClanError(msg)

        param = sig.parameters.get(arg_name)
        if param:
            param_class = param.annotation
            return param_class

        return None


API = MethodRegistry()
