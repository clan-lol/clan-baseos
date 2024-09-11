---
title: "Dev report: Providing Type-safe interfaces between NixOS and other languages"
description: "One method for creating type-safe interfaces in a nix based software stack"
authors:
  - Hsjobeki
date: 2024-09-11
slug: interfaces
---

When building a consumer-facing project on top of NixOS, one crucial question arises:
How can we provide type-safe interfaces within a polyglot software stack?

This blogpost discusses one method for creating type-safe interfaces in a software stack by using JSON-schema to maintain consistent models across layers of an application.

---

With the [clan](https://clan.lol) project, we explored one possible solution to this challenge. Our tech stack is composed of three main components:

- Nix: Handles the core business logic.
- Python: Acts as a thin wrapper, exposing the business logic through a convenient CLI and API.
- TypeScript: Manages the presentation and GUI layer, communicating with Python via an API.

This architecture is a product of our guiding principles: We aim to encapsulate as much business logic as possible in pure Nix, ensuring that anyone familiar with Nix can utilize it.

### The Challenge of Polyglot Architectures

Throughout the lifecycle of an application, architectural models, relationships, and fields are typically refined and improved over time.
By this, I refer to constructs such as classes, structs, or enums.

These elements are often required across multiple layers of the application
and must remain consistent to avoid discrepancies.
Logically, maintaining these models in a single location is crucial to prevent discrepancies and
eliminate a common source of errors—interface inconsistencies between software components.

This approach can save significant time during development cycles,
particularly in dynamically typed environments like Nix and Python,
where errors are often caught through extensive unit testing or at runtime when issues arise.

The Nix language presents a significant challenge due to its untyped and dynamic nature. Combined with NixOS, a constantly evolving collection of modules, it becomes incredibly difficult to build stable interfaces. As we develop more complex applications, a crucial question emerges: "How can models (such as classes or structs) be shared between multiple foreign languages and Nix?"

One potential solution is to define the model once in a chosen language and then generate the necessary code for all other languages. This approach ensures consistency and reduces the likelihood of errors caused by manual translations between languages.

Well-defined, statically typed models would provide build-time checks for correctness and prevent many issues and regressions that could have been avoided with robust interfaces.

Building on the earlier blog post about the [NixOS modules to JSON-schema converter](https://docs.clan.lol/blog/2024/05/25/jsonschema-converter/), a further exploration could involve using JSON-schema as an intermediate format. While not explicitly mentioned in the blog post, the JSON-schema converter operates solely on the interface declaration. It can also populate example values and other metadata that may become important later.

In our case, we decided to use NixOS module interface declarations as the source of truth, as all our models are Nix-first citizens. We will use JSON-schema as an interoperable format that can be further utilized to generate Python classes and TypeScript types.

For example, the desired Python code output could be a `TypedDict` or a `dataclass`. Since our input data might contain Nix attribute names that are invalid identifiers in Python, and vice versa, it is preferable to choose dataclasses. This allows us to store more metadata about the mapping relationships within the field properties.

```nix
# in.nix
{lib, ...}:
let
  types = lib.types;
  option = t: lib.mkOption {
    type = t;
  };
in
{
  options = {
    submodule = option (types.submodule {
      options = {
        string = option types.str;
        list-str = option (types.listOf types.str);
        attrs-str = option (types.attrsOf types.str);
      };
    });
  };
}
```

With the following nix code this can be converted into python

```nix
# convert.nix
let
  # Import clan-core flake
  clan-core = builtins.getFlake "git+https://git.clan.lol/clan/clan-core";
  pkgs = import clan-core.inputs.nixpkgs {};

  # Step 1: Convert NixOS module expression to JSON schema
  serialize = expr: builtins.toFile "in.json" (builtins.toJSON expr);
  schema = serialize ((clan-core.lib.jsonschema {}).parseModule ./in.nix);

  # classgenerator
  inherit (clan-core.packages.x86_64-linux) classgen;
in
{
  inherit schema;

  # Step 2: Generate Python classes from JSON schema
  # build with 'nix build -f convert.nix python-classes'
  python-classes = pkgs.runCommand "py-cls" {}
  ''
    ${classgen}/bin/classgen ${schema} $out
  '';
}
```

The final Python code ensures that the Python component is always in sync with the Nix code.

```python
# out.py
@dataclass
class Submodule:
    string: str
    attrs_str: dict[str, str] = field(default_factory = dict, metadata = {"alias": "attrs-str"})
    list_str: list[str] = field(default_factory = list, metadata = {"alias": "list-str"})


@dataclass
class Module:
    submodule: Submodule
```

---

However, this approach comes with some constraints for both the interface itself and the tools surrounding it:

- All types used in the interface must be JSON-serializable (e.g., Number, String, AttrSet, List, etc.).
- We identified certain constraints that work best for dataclasses, while also enhancing the final user experience:
    - Top-level options should specify a default value or be nullable.
    - Ideally, option identifiers should use names that don't require a "field-alias," although this might not always be feasible.
    - Neutral values for lists or dictionaries, such as an empty list or empty dictionary, must be supported.

The Python generator adds default constructors for dictionary and list types because the absence of a value would violate our type constraints.

It is also important to note that we control both the JSON schema converter and the class generator, which is crucial. This control allows us to limit their scope to a subset of JSON schema features and ensure interoperability between the two generators.

Another consideration is serialization and deserialization. In Python, Pydantic is typically a great choice, as it also offers [custom serializers](https://docs.pydantic.dev/latest/concepts/serialization/#custom-serializers). However, when working with NixOS modules, we chose not to emit unset or null values because they create merge conflicts in the underlying NixOS modules. We also wanted to use field-aliases for names that are invalid identifiers in Python or TypeScript and wanted validation to catch errors early (in the deserializer) between our frontend and Nix, allowing us to present well-formatted errors instead of Nix evaluation error stack traces. Nevertheless, we ultimately did not use Pydantic because we aim to follow a zero-dependency paradigm.

---

### Catching errors

Interface violations or regressions can be detected during the development cycle at build time.

```python
Submodule(string=1)
```

```sh
> Argument of type "Literal[1]" cannot be assigned to parameter "string" of type "str" in function "__init__"
  "Literal[1]" is incompatible with "str"
```

Since all our layers communicate through JSON interfaces, any potential runtime type errors are caught in Python during deserialization before they can trigger any Nix stack traces. This allows for errors to be neatly formatted for the consumer.

```python
data = {"submodule": { "string": 1  } }
checked(Model, data)

>>> Traceback (most recent call last):
>>> ...
>>> Expected string, got 1
```

---

### Future

By adopting this approach, we aim to provide a stable and secure interface for polyglot software stacks built on top of Nixpkgs,
ultimately enhancing the reliability and maintainability of complex applications.

Additionally, we will improve the overall tools and develop a library, making this methodology applicable to other projects as well.

### Links

- https://docs.clan.lol/blog/2024/05/25/jsonschema-converter/

---
