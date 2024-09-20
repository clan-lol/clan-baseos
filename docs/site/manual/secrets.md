If you want to know more about how to save and share passwords in your clan read further!

### Adding a Secret

```shellSession
clan secrets set mysecret
Paste your secret:
```

### Retrieving a Stored Secret

```bash
clan secrets get mysecret
```

### List all Secrets

```bash
clan secrets list
```

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

### Assigning Access

When using `clan secrets set <secret>` without arguments, secrets are encrypted for the key of the user named like your current $USER.

To add machines/users to an existing secret use:

```bash
 clan secrets machines add-secret <machine_name> <secret_name>
```

Alternatively specify users and machines while creating a secret:

```bash
clan secrets set --machine <machine1> --machine <machine2> --user <user1> --user <user2> <secret_name>
```

## Advanced

In this section we go into more advanced secret management topics.

### Groups

Clan CLI makes it easy to manage access by allowing you to create groups.

All users within a group inherit access to all secrets of the group.

This feature eases the process of handling permissions for multiple users.

Here's how to get started:

1. **Creating Groups**:

   Assign users to a new group, e.g., `admins`:

   ```bash
   clan secrets groups add admins <username>
   ```

2. **Listing Groups**:

   ```bash
   clan secrets groups list
   ```

3. **Assigning Secrets to Groups**:

   ```bash
   clan secrets groups add-secret <group_name> <secret_name>
   ```

### Adding Machine Keys

New machines in Clan come with age keys stored in `./sops/machines/<machine_name>`. To list these machines:

```bash
 clan secrets machines list
```

For existing machines, add their keys:

```bash
 clan secrets machines add <machine_name> <age_key>
```

To fetch an age key from an SSH host key:

```bash
 ssh-keyscan <domain_name> | nix shell nixpkgs#ssh-to-age -c ssh-to-age
```

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


## Indepth Explanation


The secrets system conceptually knows two different entities:

- **Machine**: consumes secrets
- **User**: manages access to secrets

**A Users** Can add or revoke machines' access to secrets.

**A machine** Can decrypt secrets that where encrypted specifically for that machine.

!!! Danger
    **Always make sure at least one _User_ has access to a secret**. Otherwise you could lock yourself out from accessing the secret.

### Inherited implications

By default clan uses [sops](https://github.com/getsops/sops) through [sops-nix](https://github.com/Mic92/sops-nix) for managing its secrets which inherits some implications that are important to understand:

- **Public/Private keys**: Entities are identified via their public keys. Each Entity can use their respective private key to decrypt a secret.
- **Public keys are stored**: All Public keys are stored inside the repository
- **Secrets are stored Encrypted**: secrets are stored inside the repository encrypted with the respective public keys
- **Secrets are deployed encrypted**: Fully encrypted secrets are deployed to machines at deployment time.
- **Secrets are decrypted by sops on-demand**: Each machine decrypts its secrets at runtime and stores them at an ephemeral location.
- **Machine key-pairs are auto-generated**: When a machine is created **no user-interaction is required** to setup public/private key-pairs.
- **secrets are re-encrypted**: In case machines, users or groups are modified secrets get re-encrypted on demand.

    !!! Important
        After revoking access to a secret you should also change the underlying secret. i.e. change the API key, or the password.

---

### Machine and user keys

The following diagrams illustrates how a user can provide a secret (i.e. a Password).

- By using the **Clan CLI** a user encrypts the password with both the **User public-key** and the **machine's public-key**

- The *Machine* can decrypt the password with its private-key on demand.

- The *User* is able to decrypt the password to make changes to it.

```plantuml
@startuml
!include C4_Container.puml

Person(user, "User", "Someone who manages secrets")
ContainerDb(secret, "Secret")
Container(machine, "Machine", "A Machine. i.e. Needs the Secret for a given Service." )

Rel_R(user, secret, "Encrypt", "", "Pubkeys: User, Machine")
Rel_L(secret, user, "Decrypt", "",  "user privkey")
Rel_R(secret, machine, "Decrypt", "", "machine privkey" )

@enduml
```


#### User groups

Here we illustrate how machine groups work.

Common use cases:

- **Shared Management**: Access among multiple users. I.e. a subset of secrets/machines that have two admins

```plantuml
@startuml
!include C4_Container.puml

System_Boundary(c1, "Group") {
    Person(user1, "User A", "has access")
    Person(user2, "User B", "has access")
}

ContainerDb(secret, "Secret")
Container(machine, "Machine", "A Machine. i.e. Needs the Secret for a given Service." )

Rel_R(c1, secret, "Encrypt", "", "Pubkeys: User A, User B, Machine")
Rel_R(secret, machine, "Decrypt", "", "machine privkey" )


@enduml
```

<!-- TODO: See also [Groups Reference](#groups-reference) -->

---

#### Machine groups

Here we illustrate how machine groups work.

Common use cases:

- **Shared secrets**: Among multiple machines such as Wifi passwords

```plantuml
@startuml
!include C4_Container.puml
!include C4_Deployment.puml

Person(user, "User", "Someone who manages secrets")
ContainerDb(secret, "Secret")
System_Boundary(c1, "Group") {
    Container(machine1, "Machine A", "Both machines need the same secret" )
    Container(machine2, "Machine B", "Both machines need the same secret" )
}

Rel_R(user, secret, "Encrypt", "", "Pubkeys: machine A, machine B, User")
Rel(secret, c1, "Decrypt", "", "Both machine A or B can decrypt using their private key" )


@enduml
```

<!-- TODO: See also [Groups Reference](#groups-reference) -->



See the [readme](https://github.com/Mic92/sops-nix) of sops-nix for more
examples.



