---
description = "Automatically generates and configures a password for the root user."
categories = ["System"]
features = [ "inventory" ]
---

After the system was installed/deployed the following command can be used to display the root-password:

```bash
clan secrets get {machine_name}-password
```


See also: [Facts / Secrets](../../getting-started/secrets.md)
