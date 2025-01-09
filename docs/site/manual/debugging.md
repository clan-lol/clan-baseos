# Debugging

Here are some methods for debugging and testing the clan-cli

## Using a Development Branch

To streamline your development process, I suggest not installing `clan-cli`. Instead, clone the `clan-core` repository and add `clan-core/pkgs/clan-cli/bin` to your PATH to use the checked-out version directly.

!!! Note
    After cloning, navigate to `clan-core/pkgs/clan-cli` and execute `direnv allow` to activate the devshell. This will set up a symlink to nixpkgs at a specific location; without it, `clan-cli` won't function correctly.

With this setup, you can easily use [breakpoint()](https://docs.python.org/3/library/pdb.html) to inspect the application's internal state as needed.

This approach is feasible because `clan-cli` only requires a Python interpreter and has no other dependencies.

```nix
pkgs.mkShell {
    packages = [
        pkgs.python3
    ];
    shellHook = ''
            export GIT_ROOT="$(git rev-parse --show-toplevel)"
            export PATH=$PATH:~/Projects/clan-core/pkgs/clan-cli/bin
    '';
}
```

## The Debug Flag

You can enhance your debugging process with the `--debug` flag in the `clan` command. When you add this flag to any command, it displays all subprocess commands initiated by `clan` in a readable format, along with the source code position that triggered them. This feature makes it easier to understand and trace what's happening under the hood.

```bash
$ clan machines list --debug                                                                          1 ↵
Debug log activated
nix \
    --extra-experimental-features 'nix-command flakes' \
    eval \
    --show-trace --json \
    --print-build-logs '/home/qubasa/Projects/qubasas-clan#clanInternals.machines.x86_64-linux' \
    --apply builtins.attrNames \
    --json
Caller: ~/Projects/clan-core/pkgs/clan-cli/clan_cli/machines/list.py:96::list_nixos_machines

warning: Git tree '/home/qubasa/Projects/qubasas-clan' is dirty
demo
gchq-local
wintux

```

## VSCode

If you're using VSCode, it has a handy feature that makes paths to source code files clickable in the integrated terminal. Combined with the previously mentioned techniques, this allows you to open a Clan in VSCode, execute a command like `clan machines list --debug`, and receive a printed path to the code that initiates the subprocess. With the `Ctrl` key (or `Cmd` on macOS) and a mouse click, you can jump directly to the corresponding line in the code file and add a `breakpoint()` function to it, to inspect the internal state.

## See all possible packages and tests

To quickly show all possible packages and tests execute:

```bash
nix flake show
```

Under `checks` you will find all tests that are executed in our CI. Under `packages` you find all our projects.

```
git+file:///home/lhebendanz/Projects/clan-core
├───apps
│   └───x86_64-linux
│       ├───install-vm: app
│       └───install-vm-nogui: app
├───checks
│   └───x86_64-linux
│       ├───borgbackup omitted (use '--all-systems' to show)
│       ├───check-for-breakpoints omitted (use '--all-systems' to show)
│       ├───clan-dep-age omitted (use '--all-systems' to show)
│       ├───clan-dep-bash omitted (use '--all-systems' to show)
│       ├───clan-dep-e2fsprogs omitted (use '--all-systems' to show)
│       ├───clan-dep-fakeroot omitted (use '--all-systems' to show)
│       ├───clan-dep-git omitted (use '--all-systems' to show)
│       ├───clan-dep-nix omitted (use '--all-systems' to show)
│       ├───clan-dep-openssh omitted (use '--all-systems' to show)
│       ├───"clan-dep-python3.11-mypy" omitted (use '--all-systems' to show)
├───packages
│   └───x86_64-linux
│       ├───clan-cli omitted (use '--all-systems' to show)
│       ├───clan-cli-docs omitted (use '--all-systems' to show)
│       ├───clan-ts-api omitted (use '--all-systems' to show)
│       ├───clan-app omitted (use '--all-systems' to show)
│       ├───default omitted (use '--all-systems' to show)
│       ├───deploy-docs omitted (use '--all-systems' to show)
│       ├───docs omitted (use '--all-systems' to show)
│       ├───editor omitted (use '--all-systems' to show)
└───templates
    ├───default: template: Initialize a new clan flake
    └───new-clan: template: Initialize a new clan flake
```

You can execute every test separately by following the tree path `nix run .#checks.x86_64-linux.clan-pytest -L` for example.

## Test Locally in Devshell with Breakpoints

To test the cli locally in a development environment and set breakpoints for debugging, follow these steps:

1. Run the following command to execute your tests and allow for debugging with breakpoints:
   ```bash
   cd ./pkgs/clan-cli
   pytest -n0 -s --maxfail=1 ./tests/test_nameofthetest.py
   ```
   You can place `breakpoint()` in your Python code where you want to trigger a breakpoint for debugging.

## Test Locally in a Nix Sandbox

To run tests in a Nix sandbox, you have two options depending on whether your test functions have been marked as impure or not:

### Running Tests Marked as Impure

If your test functions need to execute `nix build` and have been marked as impure because you can't execute `nix build` inside a Nix sandbox, use the following command:

```bash
nix run .#impure-checks -L
```

This command will run the impure test functions.

### Running Pure Tests

For test functions that have not been marked as impure and don't require executing `nix build`, you can use the following command:

```bash
nix build .#checks.x86_64-linux.clan-pytest --rebuild
```

This command will run all pure test functions.

### Inspecting the Nix Sandbox

If you need to inspect the Nix sandbox while running tests, follow these steps:

1. Insert an endless sleep into your test code where you want to pause the execution. For example:

   ```python
   import time
   time.sleep(3600)  # Sleep for one hour
   ```

2. Use `cntr` and `psgrep` to attach to the Nix sandbox. This allows you to interactively debug your code while it's paused. For example:

   ```bash
   psgrep <your_python_process_name>
   cntr attach <container id, container name or process id>
   ```

Or you can also use the [nix breakpoint hook](https://nixos.org/manual/nixpkgs/stable/#breakpointhook)

### What's next?

Please look into the [repo layout](./repo-layout.md) guide next!
