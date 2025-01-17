# Contributing to Clan


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
        nix profile install nixpkgs#nix-direnv-flakes nixpkgs#direnv
        ```

3. **Add direnv to your shell**:

      - Direnv needs to [hook into your shell](https://direnv.net/docs/hook.html) to work.
        You can do this by executing following command. The example below will setup direnv for `zsh` and `bash`

      ```bash
      echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc && echo 'eval "$(direnv hook bash)"' >> ~/.bashrc && eval "$SHELL"
      ```

3. **Allow the devshell**
      - Go to `clan-core/pkgs/clan-cli` and do a `direnv allow` to setup the necessary development environment to execute the `clan` command

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

## Related Projects

- **Data Mesher**: [dm](https://git.clan.lol/clan/dm)
- **Nixos Facter**: [nixos-facter](https://github.com/nix-community/nixos-facter)
- **Nixos Anywhere**: [nixos-anywhere](https://github.com/nix-community/nixos-anywhere)
- **Disko**: [disko](https://github.com/nix-community/disko)

## Fixing Bugs or Adding Features in Clan-CLI

If you have a bug fix or feature that involves a related project, clone the relevant repository and replace its invocation in your local setup.

For instance, if you need to update `nixos-anywhere` in clan-cli, find its usage:

```python
run(
    nix_shell(
        ["nixpkgs#nixos-anywhere"],
        cmd,
    ),
    RunOpts(log=Log.BOTH, prefix=machine.name, needs_user_terminal=True),
)
```

You can replace `"nixpkgs#nixos-anywhere"` with your local path:

```python
run(
    nix_shell(
        ["<path_to_local_src>#nixos-anywhere"],
        cmd,
    ),
    RunOpts(log=Log.BOTH, prefix=machine.name, needs_user_terminal=True),
)
```

# Standards

- Every new module name should be in kebab-case.
- Every fact definition, where possible should be in kebab-case.
- Every vars definition, where possible should be in kebab-case.
- Command line help descriptions should start capitalized and should not end in a period.
