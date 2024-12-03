import importlib
import json
import logging
import os
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, Any, Literal

from clan_cli.clan_uri import FlakeId
from clan_cli.cmd import run_no_stdout
from clan_cli.errors import ClanError
from clan_cli.facts import public_modules as facts_public_modules
from clan_cli.facts import secret_modules as facts_secret_modules
from clan_cli.nix import nix_build, nix_config, nix_eval, nix_metadata
from clan_cli.ssh.host import Host
from clan_cli.ssh.host_key import HostKeyCheck
from clan_cli.ssh.parse import parse_deployment_address
from clan_cli.vars.public_modules import FactStoreBase
from clan_cli.vars.secret_modules import SecretStoreBase

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from clan_cli.vars.generate import Generator


@dataclass
class Machine:
    name: str
    flake: FlakeId
    nix_options: list[str] = field(default_factory=list)
    cached_deployment: None | dict[str, Any] = None
    override_target_host: None | str = None
    host_key_check: HostKeyCheck = HostKeyCheck.STRICT

    _eval_cache: dict[str, str] = field(default_factory=dict)
    _build_cache: dict[str, Path] = field(default_factory=dict)

    def get_id(self) -> str:
        return f"{self.flake}#{self.name}"

    def flush_caches(self) -> None:
        self.cached_deployment = None
        self._build_cache.clear()
        self._eval_cache.clear()

    def __str__(self) -> str:
        return f"Machine(name={self.name}, flake={self.flake})"

    def __repr__(self) -> str:
        return str(self)

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        kwargs.update({"extra": {"command_prefix": self.name}})
        log.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        kwargs.update({"extra": {"command_prefix": self.name}})
        log.info(msg, *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        kwargs.update({"extra": {"command_prefix": self.name}})
        log.error(msg, *args, **kwargs)

    @property
    def system(self) -> str:
        # We filter out function attributes because they are not serializable.
        attr = f'(builtins.getFlake "{self.flake}").nixosConfigurations.{self.name}.pkgs.hostPlatform.system'
        output = self._eval_cache.get(attr)
        if output is None:
            output = run_no_stdout(
                nix_eval(["--impure", "--expr", attr])
            ).stdout.strip()
            self._eval_cache[attr] = output
        return json.loads(output)

    @property
    def can_build_locally(self) -> bool:
        # TODO: We could also use the function pkgs.stdenv.hostPlatform.canExecute
        # but this is good enough for now.
        output = nix_config()
        return self.system == output["system"]

    @property
    def deployment(self) -> dict:
        if self.cached_deployment is not None:
            return self.cached_deployment
        deployment = json.loads(
            self.build_nix("config.system.clan.deployment.file").read_text()
        )
        self.cached_deployment = deployment
        return deployment

    @property
    def target_host_address(self) -> str:
        # deploymentAddress is deprecated.
        val = (
            self.override_target_host
            or self.deployment.get("targetHost")
            or self.deployment.get("deploymentAddress")
        )
        if val is None:
            msg = f"'TargetHost' is not set for machine '{self.name}'"
            raise ClanError(
                msg,
                description="See https://docs.clan.lol/getting-started/deploy/#setting-the-target-host for more information.",
            )
        return val

    @property
    def secret_facts_module(
        self,
    ) -> Literal[
        "clan_cli.facts.secret_modules.sops",
        "clan_cli.facts.secret_modules.vm",
        "clan_cli.facts.secret_modules.password_store",
    ]:
        return self.deployment["facts"]["secretModule"]

    @property
    def public_facts_module(
        self,
    ) -> Literal[
        "clan_cli.facts.public_modules.in_repo", "clan_cli.facts.public_modules.vm"
    ]:
        return self.deployment["facts"]["publicModule"]

    @cached_property
    def secret_facts_store(self) -> facts_secret_modules.SecretStoreBase:
        module = importlib.import_module(self.secret_facts_module)
        return module.SecretStore(machine=self)

    @cached_property
    def public_facts_store(self) -> facts_public_modules.FactStoreBase:
        module = importlib.import_module(self.public_facts_module)
        return module.FactStore(machine=self)

    @property
    def secret_vars_module(self) -> str:
        return self.deployment["vars"]["secretModule"]

    @property
    def public_vars_module(self) -> str:
        return self.deployment["vars"]["publicModule"]

    @cached_property
    def secret_vars_store(self) -> SecretStoreBase:
        module = importlib.import_module(self.secret_vars_module)
        return module.SecretStore(machine=self)

    @cached_property
    def public_vars_store(self) -> FactStoreBase:
        module = importlib.import_module(self.public_vars_module)
        return module.FactStore(machine=self)

    @property
    def facts_data(self) -> dict[str, dict[str, Any]]:
        if self.deployment["facts"]["services"]:
            return self.deployment["facts"]["services"]
        return {}

    @property
    def vars_generators(self) -> list["Generator"]:
        from clan_cli.vars.generate import Generator

        clan_vars = self.deployment.get("vars")
        if clan_vars is None:
            return []
        generators: dict[str, Any] = clan_vars.get("generators")
        if generators is None:
            return []
        return [Generator.from_json(gen) for gen in generators.values()]

    @property
    def secrets_upload_directory(self) -> str:
        return self.deployment["facts"]["secretUploadDirectory"]

    @property
    def flake_dir(self) -> Path:
        if self.flake.is_local():
            return self.flake.path
        if self.flake.is_remote():
            return Path(nix_metadata(self.flake.url)["path"])
        msg = f"Unsupported flake url: {self.flake}"
        raise ClanError(msg)

    @property
    def target_host(self) -> Host:
        return parse_deployment_address(
            self.name,
            self.target_host_address,
            self.host_key_check,
            meta={"machine": self},
        )

    @property
    def build_host(self) -> Host:
        """
        The host where the machine is built and deployed from.
        Can be the same as the target host.
        """
        build_host = self.deployment.get("buildHost")
        if build_host is None:
            return self.target_host
        # enable ssh agent forwarding to allow the build host to access the target host
        return parse_deployment_address(
            self.name,
            build_host,
            self.host_key_check,
            forward_agent=True,
            meta={"machine": self, "target_host": self.target_host},
        )

    def nix(
        self,
        method: Literal["eval", "build"],
        attr: str,
        extra_config: None | dict = None,
        nix_options: list[str] | None = None,
    ) -> str | Path:
        """
        Build the machine and return the path to the result
        accepts a secret store and a facts store # TODO
        """
        if nix_options is None:
            nix_options = []
        config = nix_config()
        system = config["system"]

        file_info = {}
        with NamedTemporaryFile(mode="w") as config_json:
            if extra_config is not None:
                json.dump(extra_config, config_json, indent=2)
            else:
                json.dump({}, config_json)
            config_json.flush()

            file_info = json.loads(
                run_no_stdout(
                    nix_eval(
                        [
                            "--impure",
                            "--expr",
                            f'let x = (builtins.fetchTree {{ type = "file"; url = "file://{config_json.name}"; }}); in {{ narHash = x.narHash; path = x.outPath; }}',
                        ]
                    )
                ).stdout.strip()
            )

        args = []

        # get git commit from flake
        if extra_config is not None:
            metadata = nix_metadata(self.flake_dir)
            url = metadata["url"]
            if (
                "dirtyRevision" in metadata
                or "dirtyRev" in metadata["locks"]["nodes"]["clan-core"]["locked"]
            ):
                args += ["--impure"]

            args += [
                "--expr",
                f"""
                    ((builtins.getFlake "{url}").clanInternals.machinesFunc."{system}"."{self.name}" {{
                      extraConfig = builtins.fromJSON (builtins.readFile (builtins.fetchTree {{
                        type = "file";
                        url = if (builtins.compareVersions builtins.nixVersion "2.19") == -1 then "{file_info["path"]}" else "file:{file_info["path"]}";
                        narHash = "{file_info["narHash"]}";
                      }}));
                    }}).{attr}
                """,
            ]
        else:
            if (self.flake_dir / ".git").exists():
                flake = f"git+file://{self.flake_dir}"
            else:
                flake = f"path:{self.flake_dir}"

            args += [f'{flake}#clanInternals.machines."{system}".{self.name}.{attr}']
        args += nix_options + self.nix_options

        if method == "eval":
            output = run_no_stdout(nix_eval(args)).stdout.strip()
            return output
        return Path(run_no_stdout(nix_build(args)).stdout.strip())

    def eval_nix(
        self,
        attr: str,
        refresh: bool = False,
        extra_config: None | dict = None,
        nix_options: list[str] | None = None,
    ) -> str:
        """
        eval a nix attribute of the machine
        @attr: the attribute to get
        """
        if nix_options is None:
            nix_options = []
        if attr in self._eval_cache and not refresh and extra_config is None:
            return self._eval_cache[attr]

        output = self.nix("eval", attr, extra_config, nix_options)
        if isinstance(output, str):
            self._eval_cache[attr] = output
            return output
        msg = "eval_nix returned not a string"
        raise ClanError(msg)

    def build_nix(
        self,
        attr: str,
        refresh: bool = False,
        extra_config: None | dict = None,
        nix_options: list[str] | None = None,
    ) -> Path:
        """
        build a nix attribute of the machine
        @attr: the attribute to get
        """

        if nix_options is None:
            nix_options = []
        if attr in self._build_cache and not refresh and extra_config is None:
            return self._build_cache[attr]

        output = self.nix("build", attr, extra_config, nix_options)
        assert isinstance(output, Path), "Nix build did not result in a single path"
        tmp_store = os.environ.get("TMP_STORE", None)
        if tmp_store is not None:
            output = Path(f"{tmp_store}/{output!s}")
        if isinstance(output, Path):
            self._build_cache[attr] = output
            return output
        msg = "build_nix returned not a Path"
        raise ClanError(msg)
