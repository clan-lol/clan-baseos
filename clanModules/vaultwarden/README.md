---
description = "The server for the centralized password manager bitwarden"
---

After enabling the clan module, user accounts have to be created manually in the webinterface.
This is done by visiting `vaultwarden.example.com/admin` and typing in the admin password.
You can get the admin password for vaultwarden by executing:
```bash
clan secrets get  <machine-name>-vaultwarden-admin
```
To see all secrets tied to vaultwarden execute:
```bash
clan secrets list | grep vaultwarden
```
