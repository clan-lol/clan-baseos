# Disk Templates


!!! Danger ":fontawesome-solid-road-barrier: Under Construction :fontawesome-solid-road-barrier:"
    Currently under construction use with caution

    :fontawesome-solid-road-barrier: :fontawesome-solid-road-barrier: :fontawesome-solid-road-barrier:


## Structure

A disk template consists of exactly two files

- `default.nix`
- `README.md`

```sh
└── single-disk
    ├── default.nix
    └── README.md
```

## `default.nix`

Placeholders are filled with their machine specific options when a template is used for a machine.

The user can choose any valid options from the hardware report.

The file itself is then copied to `machines/{machineName}/disko.nix` and will be automatically loaded by the machine.

`single-disk/default.nix`
```
{
  disko.devices = {
    disk = {
      main = {
        device = "{{mainDisk}}";
        ...
      };
    };
  };
}
```

## Placeholders

Each template must declare the options of its placeholders depending on the hardware-report.

`api/disk.py`
```py
templates: dict[str, dict[str, Callable[[dict[str, Any]], Placeholder]]] = {
    "single-disk": {
        # Placeholders
        "mainDisk": lambda hw_report: Placeholder(
            label="Main disk", options=hw_main_disk_options(hw_report), required=True
        ),
    }
}
```

Introducing new local or global placeholders requires contributing to clan-core `api/disks.py`.

### Predefined placeholders

Some placeholders provide predefined functionality

- `uuid`: In most cases we recommend adding a unique id to all disks. This prevents the system to false boot from i.e. hot-plugged devices.
    ```
    disko.devices = {
      disk = {
        main = {
          name = "main-{{uuid}}";
          ...
        }
      }
    }
    ```


## Readme

The readme frontmatter must be of the same format as modules frontmatter.

```markdown
---
description = "Simple disk schema for single disk setups"
---

# Single disk

Use this schema for simple setups where ....

```


The format and fields of this file is not clear yet. We might change that once fully implemented.