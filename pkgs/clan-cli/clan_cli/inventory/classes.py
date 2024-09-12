# DON NOT EDIT THIS FILE MANUALLY. IT IS GENERATED.
#
# ruff: noqa: N815
# ruff: noqa: N806
# ruff: noqa: F401
# fmt: off
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class MachineDeploy:
    targetHost: None | str = field(default = None)


@dataclass
class Machine:
    deploy: MachineDeploy
    name: str
    description: None | str = field(default = None)
    icon: None | str = field(default = None)
    system: None | str = field(default = None)
    tags: list[str] = field(default_factory = list)


@dataclass
class Meta:
    name: str
    description: None | str = field(default = None)
    icon: None | str = field(default = None)


@dataclass
class Service:
    pass


@dataclass
class Inventory:
    meta: Meta
    services: Service
    machines: dict[str, Machine] = field(default_factory = dict)
