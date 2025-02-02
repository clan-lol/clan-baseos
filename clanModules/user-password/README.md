---
description = "Automatically generates and configures a password for the specified user account."
categories = ["System"]
features = ["inventory"]
---

If setting the option prompt to true, the user will be prompted to type in their desired password.

!!! Note
    This module will set `mutableUsers` to `false`, meaning you can not manage user passwords through `passwd` anymore.


After the system was installed/deployed the following command can be used to display the user-password:

```bash
clan secrets get {machine_name}-user-password
```

See also: [Facts / Secrets](../../getting-started/secrets.md)

To regenerate the password, delete the password files in the clan directory and redeploy the machine.
