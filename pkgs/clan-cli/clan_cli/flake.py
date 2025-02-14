import json
import logging
import pickle
import re
from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path
from typing import Any

from clan_cli.cmd import run
from clan_cli.dirs import user_cache_dir
from clan_cli.errors import ClanError
from clan_cli.nix import nix_build, nix_command, nix_config, nix_test_store

log = logging.getLogger(__name__)


class AllSelector:
    pass


Selector = str | int | AllSelector | set[int] | set[str]


def split_selector(selector: str) -> list[Selector]:
    """
    takes a string and returns a list of selectors.

    a selector can be:
    - a string, which is a key in a dict
    - an integer, which is an index in a list
    - a set of strings, which are keys in a dict
    - a set of integers, which are indices in a list
    - a quoted string, which is a key in a dict
    - the string "*", which selects all elements in a list or dict
    """
    pattern = r'"[^"]*"|[^.]+'
    matches = re.findall(pattern, selector)

    # Extract the matched groups (either quoted or unquoted parts)
    selectors: list[Selector] = []
    for selector in matches:
        if selector == "*":
            selectors.append(AllSelector())
        elif selector.isdigit():
            selectors.append({int(selector)})
        elif selector.startswith("{") and selector.endswith("}"):
            sub_selectors = set(selector[1:-1].split(","))
            selectors.append(sub_selectors)
        elif selector.startswith('"') and selector.endswith('"'):
            selectors.append(selector[1:-1])
        else:
            selectors.append(selector)

    return selectors


@dataclass
class FlakeCacheEntry:
    """
    a recursive structure to store the cache, with a value and a selector
    """

    def __init__(
        self,
        value: str | float | dict[str, Any] | list[Any],
        selectors: list[Selector],
        is_out_path: bool = False,
    ) -> None:
        self.value: str | float | int | dict[str | int, FlakeCacheEntry]
        self.selector: Selector

        if selectors == []:
            self.selector = AllSelector()
        elif isinstance(selectors[0], str):
            self.selector = selectors[0]
            self.value = {self.selector: FlakeCacheEntry(value, selectors[1:])}
            return
        else:
            self.selector = selectors[0]

        if is_out_path:
            if selectors != []:
                msg = "Cannot index outPath"
                raise ValueError(msg)
            if not isinstance(value, str):
                msg = "outPath must be a string"
                raise ValueError(msg)
            self.value = value

        elif isinstance(value, dict):
            if isinstance(self.selector, set):
                if not all(isinstance(v, str) for v in self.selector):
                    msg = "Cannot index dict with non-str set"
                    raise ValueError(msg)
            self.value = {}
            for key, value_ in value.items():
                if key == "outPath":
                    self.value[key] = FlakeCacheEntry(
                        value_, selectors[1:], is_out_path=True
                    )
                else:
                    self.value[key] = FlakeCacheEntry(value_, selectors[1:])

        elif isinstance(value, list):
            if isinstance(self.selector, int):
                if len(value) != 1:
                    msg = "Cannot index list with int selector when value is not singleton"
                    raise ValueError(msg)
                self.value = {}
                self.value[int(self.selector)] = FlakeCacheEntry(
                    value[0], selectors[1:]
                )
            if isinstance(self.selector, set):
                if all(isinstance(v, int) for v in self.selector):
                    self.value = {}
                    for i, v in enumerate(self.selector):
                        assert isinstance(v, int)
                        self.value[int(v)] = FlakeCacheEntry(value[i], selectors[1:])
                else:
                    msg = "Cannot index list with non-int set"
                    raise ValueError(msg)
            elif isinstance(self.selector, AllSelector):
                self.value = {}
                for i, v in enumerate(value):
                    if isinstance(v, dict | list | str | float | int):
                        self.value[i] = FlakeCacheEntry(v, selectors[1:])
            else:
                msg = f"expected integer selector or all for type list, but got {type(selectors[0])}"
                raise TypeError(msg)

        elif isinstance(value, str) and value.startswith("/nix/store/"):
            self.value = {}
            self.value["outPath"] = FlakeCacheEntry(
                value, selectors[1:], is_out_path=True
            )

        elif isinstance(value, (str | float | int)):
            self.value = value

    def insert(
        self, value: str | float | dict[str, Any] | list[Any], selectors: list[Selector]
    ) -> None:
        selector: Selector
        if selectors == []:
            selector = AllSelector()
        else:
            selector = selectors[0]

        if isinstance(selector, str):
            if isinstance(self.value, dict):
                if selector in self.value:
                    self.value[selector].insert(value, selectors[1:])
                else:
                    self.value[selector] = FlakeCacheEntry(value, selectors[1:])
                return
            msg = f"Cannot insert {selector} into non dict value"
            raise TypeError(msg)

        if isinstance(selector, AllSelector):
            self.selector = AllSelector()
        elif isinstance(self.selector, set) and isinstance(selector, set):
            self.selector.union(selector)

        if isinstance(self.value, dict) and isinstance(value, dict):
            for key, value_ in value.items():
                if key in self.value:
                    self.value[key].insert(value_, selectors[1:])
                else:
                    self.value[key] = FlakeCacheEntry(value_, selectors[1:])

        elif isinstance(self.value, dict) and isinstance(value, list):
            if isinstance(selector, set):
                if not all(isinstance(v, int) for v in selector):
                    msg = "Cannot list with non-int set"
                    raise ValueError(msg)
                for realindex, requested_index in enumerate(selector):
                    assert isinstance(requested_index, int)
                    if requested_index in self.value:
                        self.value[requested_index].insert(
                            value[realindex], selectors[1:]
                        )
            elif isinstance(selector, AllSelector):
                for index, v in enumerate(value):
                    if index in self.value:
                        self.value[index].insert(v, selectors[1:])
                    else:
                        self.value[index] = FlakeCacheEntry(v, selectors[1:])
            elif isinstance(selector, int):
                if selector in self.value:
                    self.value[selector].insert(value[0], selectors[1:])
                else:
                    self.value[selector] = FlakeCacheEntry(value[0], selectors[1:])

        elif isinstance(value, (str | float | int)):
            if self.value:
                if self.value != value:
                    msg = "value mismatch in cache, something is fishy"
                    raise TypeError(msg)
        else:
            msg = f"Cannot insert value of type {type(value)} into cache"
            raise TypeError(msg)

    def is_cached(self, selectors: list[Selector]) -> bool:
        selector: Selector
        if selectors == []:
            selector = AllSelector()
        else:
            selector = selectors[0]

        if isinstance(self.value, str | float | int):
            return selectors == []
        if isinstance(selector, AllSelector):
            if isinstance(self.selector, AllSelector):
                return all(
                    self.value[sel].is_cached(selectors[1:]) for sel in self.value
                )
            # TODO: check if we already have all the keys anyway?
            return False
        if (
            isinstance(selector, set)
            and isinstance(self.selector, set)
            and isinstance(self.value, dict)
        ):
            if not selector.issubset(self.selector):
                return False
            return all(self.value[sel].is_cached(selectors[1:]) for sel in selector)
        if isinstance(selector, str | int) and isinstance(self.value, dict):
            if selector in self.value:
                return self.value[selector].is_cached(selectors[1:])
            return False
        return False

    def select(self, selectors: list[Selector]) -> Any:
        selector: Selector
        if selectors == []:
            selector = AllSelector()
        else:
            selector = selectors[0]

        if selectors == [] and isinstance(self.value, dict) and "outPath" in self.value:
            return self.value["outPath"].value

        if isinstance(self.value, str | float | int):
            return self.value
        if isinstance(self.value, dict):
            if isinstance(selector, AllSelector):
                return {k: v.select(selectors[1:]) for k, v in self.value.items()}
            if isinstance(selector, set):
                return {
                    k: v.select(selectors[1:])
                    for k, v in self.value.items()
                    if k in selector
                }
            if isinstance(selector, str | int):
                return self.value[selector].select(selectors[1:])
        msg = f"Cannot select {selector} from type {type(self.value)}"
        raise TypeError(msg)

    def __getitem__(self, name: str) -> "FlakeCacheEntry":
        if isinstance(self.value, dict):
            return self.value[name]
        msg = f"value is a {type(self.value)}, so cannot subscribe"
        raise TypeError(msg)

    def __repr__(self) -> str:
        if isinstance(self.value, dict):
            return f"FlakeCache {{{', '.join([str(k) for k in self.value])}}}"
        return f"FlakeCache {self.value}"


class FlakeCache:
    """
    an in-memory cache for flake outputs, uses a recursive FLakeCacheEntry structure
    """

    def __init__(self) -> None:
        self.cache: FlakeCacheEntry = FlakeCacheEntry({}, [])

    def insert(self, data: dict[str, Any], selector_str: str) -> None:
        if selector_str:
            selectors = split_selector(selector_str)
        else:
            selectors = []

        self.cache.insert(data, selectors)

    def select(self, selector_str: str) -> Any:
        selectors = split_selector(selector_str)
        return self.cache.select(selectors)

    def is_cached(self, selector_str: str) -> bool:
        selectors = split_selector(selector_str)
        return self.cache.is_cached(selectors)

    def save_to_file(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            pickle.dump(self.cache, f)

    def load_from_file(self, path: Path) -> None:
        if path.exists():
            with path.open("rb") as f:
                self.cache = pickle.load(f)


@dataclass
class Flake:
    """
    This class represents a flake, and is used to interact with it.
    values can be accessed using the select method, which will fetch the value from the cache if it is present.
    """

    identifier: str

    def __post_init__(self) -> None:
        self._cache: FlakeCache | None = None
        self._path: Path | None = None
        self._is_local: bool | None = None

    @classmethod
    def from_json(cls: type["Flake"], data: dict[str, Any]) -> "Flake":
        return cls(data["identifier"])

    def __str__(self) -> str:
        return self.identifier

    def __hash__(self) -> int:
        return hash(self.identifier)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Flake):
            return NotImplemented
        return self.identifier == other.identifier

    @property
    def is_local(self) -> bool:
        if self._is_local is None:
            self.prefetch()
        assert isinstance(self._is_local, bool)
        return self._is_local

    @property
    def path(self) -> Path:
        if self._path is None:
            self.prefetch()
        assert isinstance(self._path, Path)
        return self._path

    def prefetch(self) -> None:
        flake_prefetch = run(
            nix_command(
                [
                    "flake",
                    "prefetch",
                    "--json",
                    "--option",
                    "flake-registry",
                    "",
                    self.identifier,
                ]
            )
        )
        flake_metadata = json.loads(flake_prefetch.stdout)
        self.store_path = flake_metadata["storePath"]
        self.hash = flake_metadata["hash"]

        self._cache = FlakeCache()
        hashed_hash = sha1(self.hash.encode()).hexdigest()
        self.flake_cache_path = Path(user_cache_dir()) / "clan" / "flakes" / hashed_hash
        if self.flake_cache_path.exists():
            self._cache.load_from_file(self.flake_cache_path)

        if flake_metadata["original"].get("url", "").startswith("file:"):
            self._is_local = True
            path = flake_metadata["original"]["url"].removeprefix("file://")
            path = path.removeprefix("file:")
            self._path = Path(path)
        elif flake_metadata["original"].get("path"):
            self._is_local = True
            self._path = Path(flake_metadata["original"]["path"])
        else:
            self._is_local = False
            self._path = Path(self.store_path)

    def get_from_nix(self, selectors: list[str]) -> None:
        if self._cache is None:
            self.prefetch()
        assert self._cache is not None

        config = nix_config()
        nix_code = f"""
            let
              flake = builtins.getFlake("path:{self.store_path}?narHash={self.hash}");
            in
              flake.inputs.nixpkgs.legacyPackages.{config["system"]}.writeText "clan-flake-select" (builtins.toJSON [ ({" ".join([f'flake.clanInternals.lib.select "{attr}" flake' for attr in selectors])}) ])
        """
        build_output = Path(run(nix_build(["--expr", nix_code])).stdout.strip())
        if tmp_store := nix_test_store():
            build_output = tmp_store.joinpath(*build_output.parts[1:])
        outputs = json.loads(build_output.read_text())
        if len(outputs) != len(selectors):
            msg = f"flake_prepare_cache: Expected {len(outputs)} outputs, got {len(outputs)}"
            raise ClanError(msg)
        self._cache.load_from_file(self.flake_cache_path)
        for i, selector in enumerate(selectors):
            self._cache.insert(outputs[i], selector)
        self._cache.save_to_file(self.flake_cache_path)

    def select(self, selector: str) -> Any:
        if self._cache is None:
            self.prefetch()
        assert self._cache is not None

        self._cache.load_from_file(self.flake_cache_path)
        if not self._cache.is_cached(selector):
            log.info(f"Cache miss for {selector}")
            self.get_from_nix([selector])
        return self._cache.select(selector)
