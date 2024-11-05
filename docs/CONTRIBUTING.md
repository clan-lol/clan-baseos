# Contributing

**Continuous Integration (CI)**: Each pull request gets automatically tested by gitea. If any errors are detected, it will block pull requests until they're resolved.

**Dependency Management**: We use the [Nix package manager](https://nixos.org/) to manage dependencies and ensure reproducibility, making your development process more robust.

## Supported Operating Systems

- Linux
- macOS

# Getting Started with the Development Environment

Let's get your development environment up and running:

1. **Install Nix Package Manager**:

      - You can install the Nix package manager by either [downloading the Nix installer](https://github.com/DeterminateSystems/nix-installer/releases) or running this command:
        ```bash
        curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install
        ```

2. **Install direnv**:

      - To automatically setup a devshell on entering the directory
        ```bash
        nix profile install nixpkgs#nix-direnv-flakes
        ```

3. **Add direnv to your shell**:

      - Direnv needs to [hook into your shell](https://direnv.net/docs/hook.html) to work.
        You can do this by executing following command. The example below will setup direnv for `zsh` and `bash`

      ```bash
      echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc && echo 'eval "$(direnv hook bash)"' >> ~/.bashrc && eval "$SHELL"
      ```

4. **Create a Gitea Account**:
      - Register an account on https://git.clan.lol
      - Fork the [clan-core](https://git.clan.lol/clan/clan-core) repository
      - Clone the repository and navigate to it
      - Add a new remote called upstream:
         ```bash
         git remote add upstream gitea@git.clan.lol:clan/clan-core.git
         ```
5. **Create an access token**:
      - Log in to Gitea.
      - Go to your account settings.
      - Navigate to the Applications section.
      - Click Generate New Token.
      - Name your token and select all available scopes.
      - Generate the token and copy it for later use.
      - Your access token is now ready to use with all permissions.

5. **Register Your Gitea Account Locally**:

      - Execute the following command to add your Gitea account locally:
        ```bash
        tea login add
        ```
      - Fill out the prompt as follows:
        - URL of Gitea instance: `https://git.clan.lol`
        - Name of new Login [git.clan.lol]:
        - Do you have an access token? Yes
        - Token: <yourtoken>
        - Set Optional settings: No


6. **Allow .envrc**:

      - When you enter the directory, you'll receive an error message like this:
        ```bash
        direnv: error .envrc is blocked. Run `direnv allow` to approve its content
        ```
      - Execute `direnv allow` to automatically execute the shell script `.envrc` when entering the directory.

7. **(Optional) Install Git Hooks**:
      - To syntax check your code you can run:
         ```bash
         nix fmt
         ```
      - To make this automatic install the git hooks
         ```bash
         ./scripts/pre-commit
         ```

8. **Open a Pull Request**:
      - To automatically open up a pull request you can use our tool called:
      ```
      merge-after-ci --reviewers Mic92 Lassulus Qubasa
      ```

# Debugging

Here are some methods for debugging and testing the clan-cli:

## See all possible packages and tests

To quickly show all possible packages and tests execute:

```bash
nix flake show --system no-eval
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

You can execute every test separately by following the tree path `nix build .#checks.x86_64-linux.clan-pytest` for example.

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
nix run .#impure-checks
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
   psgrep -a -x your_python_process_name
   cntr attach <container id, container name or process id>
   ```

Or you can also use the [nix breakpoint hook](https://nixos.org/manual/nixpkgs/stable/#breakpointhook)


# Standards

- Every new module name should be in kebab-case.
- Every fact definition, where possible should be in kebab-case.
- Every vars definition, where possible should be in kebab-case.
