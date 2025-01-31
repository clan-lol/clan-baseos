# mypy: disable-error-code="var-annotated"

import json
from pathlib import Path
from typing import Any

import pytest
from clan_cli.clan_uri import FlakeId
from clan_cli.locked_open import locked_open
from clan_cli.templates import get_clan_nix_attrset
from fixtures_flakes import FlakeForTest


# Function to write clan attributes to a file
def write_clan_attr(clan_attrset: dict[str, Any], flake: FlakeForTest) -> None:
    file = flake.path / "clan_attrs.json"
    with locked_open(file, "w") as cfile:
        json.dump(clan_attrset, cfile, indent=2)


# Common function to test clan nix attrset
def nix_attr_tester(
    test_flake: FlakeForTest,
    injected: dict[str, Any],
    expected: dict[str, Any],
    test_number: int,
) -> None:
    write_clan_attr(injected, test_flake)
    nix_attrset = get_clan_nix_attrset(FlakeId(str(test_flake.path)))

    assert json.dumps(nix_attrset, indent=2) == json.dumps(expected, indent=2)


# Test Case 1: Minimal input with empty templates
@pytest.mark.impure
def test_clan_get_nix_attrset_case_1(
    monkeypatch: pytest.MonkeyPatch, temporary_home: Path, test_flake: FlakeForTest
) -> None:
    test_number = 1
    injected = {"templates": {"clan": {}}}
    expected = {"inputs": {}, "self": {"templates": {"clan": {}}}}
    nix_attr_tester(test_flake, injected, expected, test_number)


# Test Case 2: Input with one template under 'clan'
@pytest.mark.impure
def test_clan_get_nix_attrset_case_2(
    monkeypatch: pytest.MonkeyPatch, temporary_home: Path, test_flake: FlakeForTest
) -> None:
    test_number = 2
    injected = {
        "templates": {
            "clan": {
                "example_template": {
                    "description": "An example clan template.",
                    "path": "/example/path",
                }
            }
        }
    }
    expected = {
        "inputs": {},
        "self": {
            "templates": {
                "clan": {
                    "example_template": {
                        "description": "An example clan template.",
                        "path": "/example/path",
                    }
                }
            }
        },
    }
    nix_attr_tester(test_flake, injected, expected, test_number)


# Test Case 3: Input with templates under multiple types
@pytest.mark.impure
def test_clan_get_nix_attrset_case_3(
    monkeypatch: pytest.MonkeyPatch, temporary_home: Path, test_flake: FlakeForTest
) -> None:
    test_number = 3
    injected = {
        "templates": {
            "clan": {
                "clan_template": {
                    "description": "A clan template.",
                    "path": "/clan/path",
                }
            },
            "disko": {
                "disko_template": {
                    "description": "A disko template.",
                    "path": "/disko/path",
                }
            },
            "machine": {
                "machine_template": {
                    "description": "A machine template.",
                    "path": "/machine/path",
                }
            },
        }
    }
    expected = {
        "inputs": {},
        "self": {
            "templates": {
                "clan": {
                    "clan_template": {
                        "description": "A clan template.",
                        "path": "/clan/path",
                    }
                },
                "disko": {
                    "disko_template": {
                        "description": "A disko template.",
                        "path": "/disko/path",
                    }
                },
                "machine": {
                    "machine_template": {
                        "description": "A machine template.",
                        "path": "/machine/path",
                    }
                },
            }
        },
    }
    nix_attr_tester(test_flake, injected, expected, test_number)


# Test Case 4: Input with modules only
@pytest.mark.impure
def test_clan_get_nix_attrset_case_4(
    monkeypatch: pytest.MonkeyPatch, temporary_home: Path, test_flake: FlakeForTest
) -> None:
    test_number = 4
    injected = {
        "modules": {
            "module1": {"description": "First module", "path": "/module1/path"},
            "module2": {"description": "Second module", "path": "/module2/path"},
        }
    }
    expected = {
        "inputs": {},
        "self": {
            "modules": {
                "module1": {"description": "First module", "path": "/module1/path"},
                "module2": {"description": "Second module", "path": "/module2/path"},
            },
        },
    }
    nix_attr_tester(test_flake, injected, expected, test_number)


# Test Case 5: Input with both templates and modules
@pytest.mark.impure
def test_clan_get_nix_attrset_case_5(
    monkeypatch: pytest.MonkeyPatch, temporary_home: Path, test_flake: FlakeForTest
) -> None:
    test_number = 5
    injected = {
        "templates": {
            "clan": {
                "clan_template": {
                    "description": "A clan template.",
                    "path": "/clan/path",
                }
            }
        },
        "modules": {
            "module1": {"description": "First module", "path": "/module1/path"}
        },
    }
    expected = {
        "inputs": {},
        "self": {
            "modules": {
                "module1": {"description": "First module", "path": "/module1/path"}
            },
            "templates": {
                "clan": {
                    "clan_template": {
                        "description": "A clan template.",
                        "path": "/clan/path",
                    }
                }
            },
        },
    }
    nix_attr_tester(test_flake, injected, expected, test_number)


# Test Case 6: Input with missing 'templates' and 'modules' (empty clan attrset)
@pytest.mark.impure
def test_clan_get_nix_attrset_case_6(
    monkeypatch: pytest.MonkeyPatch, temporary_home: Path, test_flake: FlakeForTest
) -> None:
    test_number = 6
    injected = {}
    expected = {"inputs": {}, "self": {}}
    nix_attr_tester(test_flake, injected, expected, test_number)
