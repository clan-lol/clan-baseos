# Secrets / Facts

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

---

## Whats next?

- [Deployment](deploy.md): How to remotely deploy your machine
- [Advanced Secrets](../manual/secrets.md) If you want to know more about how to save and share passwords in your clan 

