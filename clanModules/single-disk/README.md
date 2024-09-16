---
description = "Configures partitioning of the main disk"
categories = ["System"]
features = [ "inventory" ]
---
# Primary Disk Layout

A module for the "disk-layout" category MUST be choosen.

There is exactly one slot for this type of module in the UI, if you don't fill the slot, your machine cannot boot

This module is a good choice for most machines. In the future clan will offer a broader choice of disk-layouts

The UI will ask for the options of this module:

`device: "/dev/null"`

# Usage example

`inventory.json`
```json
"services": {
    "single-disk": {
        "default": {
            "meta": {
                "name": "single-disk"
            },
            "roles": {
                "default": {
                    "machines": ["jon"]
                }
            },
            "machines": {
                "jon": {
                    "config": {
                        "device": "/dev/null"
                    }
                }
            }
        }
    }
}
```