# Secrets / Facts

Clan enables encryption of secrets (such as passwords & keys) ensuring security and ease-of-use among users.

Clan utilizes the [sops](https://github.com/getsops/sops) format and integrates with [sops-nix](https://github.com/Mic92/sops-nix) on NixOS machines.

This documentation will guide you through managing secrets with the Clan CLI

## 1. Initializing Secrets

### Create Your Master Keypair

To get started, you'll need to create **Your master keypair**.

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
    If it's lost, you won't be able to get to your secrets anymore because they all need the master key to be unlocked.

!!! note 
    It's safe to add any secrets created by the clan CLI and placed in your repository to version control systems like `git`.

### Add Your Public Key

```bash
clan secrets users add <your_username> <your_public_key>
```

!!! note 
    Choose the same username as on your Setup/Source Machine that you use to control the deployment with.

Once run this will create the following files:

```{.console, .no-copy}
sops/
└── users/
    └── <your_username>/
        └── key.json
```

## 2. Adding Machine Keys

New machines in Clan come with age keys stored in `./sops/machines/<machine_name>`. To list these machines:

```bash
$ clan secrets machines list
```

For existing machines, add their keys:

```bash
$ clan secrets machines add <machine_name> <age_key>
```

### Advanced

To fetch an age key from an SSH host key:

```bash
$ ssh-keyscan <domain_name> | nix shell nixpkgs#ssh-to-age -c ssh-to-age
```

## 3. Assigning Access

By default, secrets are encrypted for your key. To specify which users and machines can access a secret:

```bash
$ clan secrets set --machine <machine1> --machine <machine2> --user <user1> --user <user2> <secret_name>
```

You can add machines/users to existing secrets without modifying the secret:

```bash
$ clan secrets machines add-secret <machine_name> <secret_name>
```

## 4. Adding Secrets

```bash
$ clan secrets set mysecret
Paste your secret: 
```

!!! note 
    As you type your secret won't be displayed. Press Enter to save the secret.

## 5. Retrieving Stored Secrets

```bash
$ clan secrets get mysecret
```

### List all Secrets

```bash
$ clan secrets list
```

## 6. Groups

Clan CLI makes it easy to manage access by allowing you to create groups.

All users within a group inherit access to all secrets of the group.

This feature eases the process of handling permissions for multiple users.

Here's how to get started:

1. **Creating Groups**:

   Assign users to a new group, e.g., `admins`:

   ```bash
   $ clan secrets groups add admins <username>
   ```

2. **Listing Groups**:

   ```bash
   $ clan secrets groups list
   ```

3. **Assigning Secrets to Groups**:

   ```bash
   $ clan secrets groups add-secret <group_name> <secret_name>
   ```

## Further

Secrets in the repository follow this structure:

```{.console, .no-copy}
sops/
├── secrets/
│   └── <secret_name>/
│       ├── secret
│       └── users/
│           └── <your_username>/
```

The content of the secret is stored encrypted inside the `secret` file under `mysecret`.

By default, secrets are encrypted with your key to ensure readability.

### NixOS integration

A NixOS machine will automatically import all secrets that are encrypted for the
current machine. At runtime it will use the host key to decrypt all secrets into
an in-memory, non-persistent filesystem using [sops-nix](https://github.com/Mic92/sops-nix). 
In your nixos configuration you can get a path to secrets like this `config.sops.secrets.<name>.path`. For example:

```nix
{ config, ...}: {
  sops.secrets.my-password.neededForUsers = true;

  users.users.mic92 = {
    isNormalUser = true;
    passwordFile = config.sops.secrets.my-password.path;
  };
}
```

See the [readme](https://github.com/Mic92/sops-nix) of sops-nix for more
examples.

### Migration: Importing existing sops-based keys / sops-nix

`clan secrets` stores each secret in a single file, whereas [sops](https://github.com/Mic92/sops-nix) commonly allows to put all secrets in a yaml or json document.

If you already happened to use sops-nix, you can migrate by using the `clan secrets import-sops` command by importing these files:

```bash
% clan secrets import-sops --prefix matchbox- --group admins --machine matchbox nixos/matchbox/secrets/secrets.yaml
```

This will create secrets for each secret found in `nixos/matchbox/secrets/secrets.yaml` in a `./sops` folder of your repository.
Each member of the group `admins` in this case will be able to decrypt the secrets with their respective key.

Since our clan secret module will auto-import secrets that are encrypted for a particular nixos machine,
you can now remove `sops.secrets.<secrets> = { };` unless you need to specify more options for the secret like owner/group of the secret file.
