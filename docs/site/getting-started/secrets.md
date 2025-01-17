
Clan enables encryption of secrets (such as passwords & keys) ensuring security and ease-of-use among users.

Clan utilizes the [sops](https://github.com/getsops/sops) format and integrates with [sops-nix](https://github.com/Mic92/sops-nix) on NixOS machines.

This guide will walk you through:

- **Creating a Keypair for Your User**: Learn how to generate a keypair for $USER to securely control all secrets.
- **Creating Your First Secret**: Step-by-step instructions on creating your initial secret.
- **Assigning Machine Access to the Secret**: Understand how to grant a machine access to the newly created secret.

## Create Your Admin Keypair

To get started, you'll need to create **Your admin keypair**.

!!! info
    Don't worry — if you've already made one before, this step won't change or overwrite it.

```bash
clan secrets key generate
```

**Output**:

```{.console, .no-copy}
Public key: age1wkth7uhpkl555g40t8hjsysr20drq286netu8zptw50lmqz7j95sw2t3l7

Generated age private key at '/home/joerg/.config/sops/age/keys.txt' for your user. Please back it up on a secure location or you will lose access to your secrets.
Also add your age public key to the repository with 'clan secrets users add YOUR_USER age1wkth7uhpkl555g40t8hjsysr20drq286netu8zptw50lmqz7j95sw2t3l7' (replace YOUR_USER with your actual username)
```

!!! warning
    Make sure to keep a safe backup of the private key you've just created.
    If it's lost, you won't be able to get to your secrets anymore because they all need the admin key to be unlocked.

!!! note
    It's safe to add any secrets created by the clan CLI and placed in your repository to version control systems like `git`.

### Add Your Public Key

```bash
clan secrets users add $USER <your_public_key>
```

It's best to choose the same username as on your Setup/Admin Machine that you use to control the deployment with.

Once run this will create the following files:

```{.console, .no-copy}
sops/
└── users/
    └── <your_username>/
        └── key.json
```
If you followed the quickstart tutorial all necessary secrets are initialized at this point.



### Generate Facts and Vars

Typically, this step is handled automatically when a machine is deployed. However, to enable the use of `nix flake check` with your configuration, it must be completed manually beforehand.

Currently, generating all the necessary facts requires two separate commands. This is due to the coexistence of two parallel secret management solutions: the older, stable version (`clan secrets` and `clan facts`) and the newer, experimental version (`clan vars`).

To generate both facts and vars, execute the following commands:

```sh
clan facts generate && clan vars generate
```


### Check Configuration

Validate your configuration by running:

```bash
nix flake check
```

This command helps ensure that your system configuration is correct and free from errors.

!!! Tip

    You can integrate this step into your [Continuous Integration](https://en.wikipedia.org/wiki/Continuous_integration) workflow to ensure that only valid Nix configurations are merged into your codebase.

