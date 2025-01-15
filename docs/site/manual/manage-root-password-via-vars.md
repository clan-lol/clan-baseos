# Managing the root password declaratively using `vars`

Defining a linux user's password via the nixos configuration previously required running `mkpasswd ...` and then copying the hash back into the nix configuration.

In this example, we will guide you through automating that interaction using clan `vars`.

For a more general exaplanation of what clan vars are and how it works, see the intro of the [Reference Documentation for vars](https://docs.clan.lol/reference/clan-core/vars/)

This guide assumes
- clan is set up already (see [Getting Started](../getting-started/index.md))
- a machine has been added to the clan (see [Adding Machines](./adding-machines.md))

This section will walk you through the following steps:

1. declare a `generator` in the machine's nixos configuration
2. inspect the status via the clan cli
3. generate the vars
4. observer the changes
5. update the machine
6. share the root password between machines
7. change the password

## Declare the generator

In this example, a `vars` `generator` is used to:

- prompt the user for the password
- run the required `mkpasswd` command to generate the hash
- store the hash in a file
- expose the file path to the nixos configuration

Create a new nix file `root-password.nix` with the following content and import it into your `configuration.nix`
```nix
{config, pkgs, ...}: {

  clan.core.vars.generators.root-password = {
    # prompt the user for a password
    # (`password-input` being an arbitrary name)
    prompts.password-input.description = "the root user's password";
    prompts.password-input.type = "hidden";
    # don't store the prompted password itself
    prompts.password-input.persist = false;
    # define an output file for storing the hash
    files.password-hash.secret = false;
    # define the logic for generating the hash
    script = ''
      cat $prompts/password-input | mkpasswd -m sha-512 > $out/password-hash
    '';
    # the tools required by the script
    runtimeInputs = [ pkgs.mkpasswd ];
  };

  # ensure users are immutable (otherwise the following config might be ignored)
  users.mutableUsers = false;
  # set the root password to the file containing the hash
  users.users.root.hashedPasswordFile =
    # clan will make sure, this path exists
    config.clan.core.vars.generators.root-password.files.password-hash.path;
}
```

## Inspect the status

Executing `clan vars list`, you should see the following:
```shellSession
$ clan vars list my_machine
root-password/password-hash: <not set>
```

...indicating that the value `password-hash` for the generator `root-password` is not set yet.

## Generate the values

This step is not strictly necessary, as deploying the machine via `clan machines update` would trigger the generator as well.

To run the generator, execute `clan vars generate` for your machine
```shellSession
$ clan vars generate my_machine
Enter the value for root-password/password-input (hidden):
```

After entering the value, the updated status is reported:
```shellSession
Updated var root-password/password-hash
  old: <not set>
  new: $6$RMats/YMeypFtcYX$DUi...
```

## Observe the changes

With the last step, a new file was created in your repository:
`vars/per-machine/my-machine/root-password/password-hash/value`

If the repository is a git repository, a commit was created automatically:
```shellSession
$ git log -n1
commit ... (HEAD -> master)
Author: ...
Date:   ...

    Update vars via generator root-password for machine grmpf-nix
```

## Update the machine

```shell
clan machines update my_machine
```

## Share root password between machines

If we just imported the `root-password.nix` from above into more machines, clan would ask for a new password for each additional machine.

If the root password instead should only be entered once and shared across all machines, the generator defined above needs to be declard as `shared`, by adding `share = true` to it:
```nix
{config, pkgs, ...}: {
  clan.vars.generators.root-password = {
    share = true;
    # ...
  }
}
```

Importing that shared generator into each machine, will ensure that the pasword is only asked once the first machine gets updated and then re-used for all subsequent machines.

## Change the root password

Changing the password can be done via this command.
Replace `my-machine` with your machine.
If the password is shared, just pick any machine that has the generator declared.

```shellSession
$ clan vars generate my-machine --generator root-password --regenerate
...
Enter the value for root-password/password-input (hidden):
Input received. Processing...
...
Updated var root-password/password-hash
  old: $6$tb27m6EOdff.X9TM$19N...

  new: $6$OyoQtDVzeemgh8EQ$zRK...
```


## Further Reading

- [Reference Documentation for `clan.core.vars` nixos options](../reference/clan-core/vars.md)
- [Reference Documentation for the `clan vars` cli command](../reference/cli/vars.md)
