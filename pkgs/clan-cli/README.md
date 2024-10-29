# clan-cli

The clan-cli contains the command line interface

## Hacking on the cli

We recommend setting up [direnv](https://direnv.net/) to load the development with nix.
If you do not have it set up you can also use `nix develop` directly like this:

```
use flake .#clan-cli --builders ''
```

After you can use the local bin wrapper to test things in the cli:

```
./bin/clan
```

## Run locally single-threaded for debugging

By default tests run in parallel using pytest-parallel.
pytest-parallel however breaks `breakpoint()`. To disable it, use this:

```bash
pytest -n0 -s
```

You can also run a single test like this:

```bash
pytest -n0 -s tests/test_secrets_cli.py::test_users
```

## Run tests in nix container

Run all impure checks

```bash
nix run .#impure-checks
```

Run all checks

```bash
nix flake check
```
