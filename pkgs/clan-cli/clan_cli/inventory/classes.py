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
class AdminConfig:
    allowedKeys: dict[str, str] = field(default_factory = dict)


@dataclass
class ServiceAdminMachine:
    config: AdminConfig = field(default_factory = AdminConfig)
    imports: list[str] = field(default_factory = list)


@dataclass
class ServiceMeta:
    name: str
    description: None | str = field(default = None)
    icon: None | str = field(default = None)


@dataclass
class ServiceAdminRoleDefault:
    config: AdminConfig = field(default_factory = AdminConfig)
    imports: list[str] = field(default_factory = list)
    machines: list[str] = field(default_factory = list)
    tags: list[str] = field(default_factory = list)


@dataclass
class ServiceAdminRole:
    default: ServiceAdminRoleDefault


@dataclass
class ServiceAdmin:
    meta: ServiceMeta
    roles: ServiceAdminRole
    config: AdminConfig = field(default_factory = AdminConfig)
    machines: dict[str, ServiceAdminMachine] = field(default_factory = dict)


@dataclass
class BorgbackupConfigDestination:
    name: str
    repo: str


@dataclass
class BorgbackupConfig:
    destinations: dict[str, BorgbackupConfigDestination] = field(default_factory = dict)
    exclude: list[str] = field(default_factory = list)


@dataclass
class ServiceBorgbackupMachine:
    config: BorgbackupConfig = field(default_factory = BorgbackupConfig)
    imports: list[str] = field(default_factory = list)


@dataclass
class ServiceBorgbackupRoleClient:
    config: BorgbackupConfig = field(default_factory = BorgbackupConfig)
    imports: list[str] = field(default_factory = list)
    machines: list[str] = field(default_factory = list)
    tags: list[str] = field(default_factory = list)


@dataclass
class ServiceBorgbackupRoleServer:
    config: BorgbackupConfig = field(default_factory = BorgbackupConfig)
    imports: list[str] = field(default_factory = list)
    machines: list[str] = field(default_factory = list)
    tags: list[str] = field(default_factory = list)


@dataclass
class ServiceBorgbackupRole:
    client: ServiceBorgbackupRoleClient
    server: ServiceBorgbackupRoleServer


@dataclass
class ServiceBorgbackup:
    meta: ServiceMeta
    roles: ServiceBorgbackupRole
    config: BorgbackupConfig = field(default_factory = BorgbackupConfig)
    machines: dict[str, ServiceBorgbackupMachine] = field(default_factory = dict)


@dataclass
class IwdConfigNetwork:
    ssid: str


@dataclass
class IwdConfig:
    networks: dict[str, IwdConfigNetwork] = field(default_factory = dict)


@dataclass
class ServiceIwdMachine:
    config: IwdConfig = field(default_factory = IwdConfig)
    imports: list[str] = field(default_factory = list)


@dataclass
class ServiceIwdRoleDefault:
    config: IwdConfig = field(default_factory = IwdConfig)
    imports: list[str] = field(default_factory = list)
    machines: list[str] = field(default_factory = list)
    tags: list[str] = field(default_factory = list)


@dataclass
class ServiceIwdRole:
    default: ServiceIwdRoleDefault


@dataclass
class ServiceIwd:
    meta: ServiceMeta
    roles: ServiceIwdRole
    config: IwdConfig = field(default_factory = IwdConfig)
    machines: dict[str, ServiceIwdMachine] = field(default_factory = dict)


@dataclass
class PackagesConfig:
    packages: list[str] = field(default_factory = list)


@dataclass
class ServicePackageMachine:
    config: PackagesConfig = field(default_factory = PackagesConfig)
    imports: list[str] = field(default_factory = list)


@dataclass
class ServicePackageRoleDefault:
    config: PackagesConfig = field(default_factory = PackagesConfig)
    imports: list[str] = field(default_factory = list)
    machines: list[str] = field(default_factory = list)
    tags: list[str] = field(default_factory = list)


@dataclass
class ServicePackageRole:
    default: ServicePackageRoleDefault


@dataclass
class ServicePackage:
    meta: ServiceMeta
    roles: ServicePackageRole
    config: PackagesConfig = field(default_factory = PackagesConfig)
    machines: dict[str, ServicePackageMachine] = field(default_factory = dict)


@dataclass
class SingleDiskConfig:
    device: None | str = field(default = None)


@dataclass
class ServiceSingleDiskMachine:
    config: SingleDiskConfig = field(default_factory = SingleDiskConfig)
    imports: list[str] = field(default_factory = list)


@dataclass
class ServiceSingleDiskRoleDefault:
    config: SingleDiskConfig = field(default_factory = SingleDiskConfig)
    imports: list[str] = field(default_factory = list)
    machines: list[str] = field(default_factory = list)
    tags: list[str] = field(default_factory = list)


@dataclass
class ServiceSingleDiskRole:
    default: ServiceSingleDiskRoleDefault


@dataclass
class ServiceSingleDisk:
    meta: ServiceMeta
    roles: ServiceSingleDiskRole
    config: SingleDiskConfig = field(default_factory = SingleDiskConfig)
    machines: dict[str, ServiceSingleDiskMachine] = field(default_factory = dict)


@dataclass
class Service:
    admin: dict[str, ServiceAdmin] = field(default_factory = dict)
    borgbackup: dict[str, ServiceBorgbackup] = field(default_factory = dict)
    iwd: dict[str, ServiceIwd] = field(default_factory = dict)
    packages: dict[str, ServicePackage] = field(default_factory = dict)
    single_disk: dict[str, ServiceSingleDisk] = field(default_factory = dict, metadata = {"alias": "single-disk"})


@dataclass
class Inventory:
    meta: Meta
    services: Service
    machines: dict[str, Machine] = field(default_factory = dict)
