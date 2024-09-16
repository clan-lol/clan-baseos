---
description = "Statically configure borgbackup with sane defaults."
---
!!! Danger "Deprecated"
    Use [borgbackup](borgbackup.md) instead.

    Don't use borgbackup-static through [inventory](../../guides/inventory.md).

This module implements the `borgbackup` backend and implements sane defaults
for backup management through `borgbackup` for members of the clan.

Configure target machines where the backups should be sent to through `targets`.

Configure machines that should be backuped either through `includeMachines`
which will exclusively add the included machines to be backuped, or through
`excludeMachines`, which will add every machine except the excluded machine to the backup.
