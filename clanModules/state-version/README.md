---
description = "Automatically generate the state version of the nixos installation."
features = [ "inventory" ]
---

This module generates the `system.stateVersion` of the nixos installation automatically.

Options: [system.stateVersion](https://search.nixos.org/options?channel=unstable&show=system.stateVersion&from=0&size=50&sort=relevance&type=packages&query=stateVersion)

Migration:
If you are already setting `system.stateVersion`, then import the module and then either let the automatic generation happen, or trigger the generation manually for the machine. The module will take the specified version, if one is already supplied through the config.
To manually generate the version for a specified machine run:

```
clan vars generate [MACHINE]
```

If the setting was already set you can then remove `system.stateVersion` from your machine configuration. For new machines, just import the module.
