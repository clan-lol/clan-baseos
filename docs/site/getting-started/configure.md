
Managing machine configurations can be done in the following ways:

- writing `nix` expressions in a `flake.nix` file,
- placing `autoincluded` files into your machine directory,
- configuring everything in a simple UI (upcoming).

Clan currently offers the following methods to configure machines:

!!! Success "Recommended for nix people"

    - flake.nix (i.e. via `buildClan`)
        - `machine` argument
        - `inventory` argument

    - machines/`machine_name`/configuration.nix (`autoincluded` if it exists)

    See the complete [list](../manual/adding-machines.md#automatic-registration) of auto-loaded files.

???+ Note "Used by CLI & UI"

    - inventory.json


## Global configuration

In the `flake.nix` file:

- [x] set a unique `name`.

=== "**normal flake template**"

    ```nix title="flake.nix" hl_lines="3"
    buildClan {
        # Set a unique name
        meta.name = "Lobsters";
        # Should usually point to the directory of flake.nix
        directory = ./.;
    }
    ```

=== "**template using flake-parts**"

    !!! info "See [Clan with flake-parts](../manual/flake-parts.md) for help migrating to flake-parts."

    ```nix title="flake.nix" hl_lines="3"
    clan = {
        # Set a unique name
        meta.name = "Lobsters";
    };
    ```

## Machine configuration

Adding or configuring a new machine requires two simple steps:

### Step 1. Identify Target Disk-ID

1. Find the remote disk id by executing:

    ```bash title="setup computer"
    ssh root@<IP> lsblk --output NAME,ID-LINK,FSTYPE,SIZE,MOUNTPOINT
    ```

    !!! Note
        Replace `<IP>` with the IP address of the machine if you don't have the avahi service running which resolves mDNS local domains.

    Which should show something like:

    ```{.shellSession hl_lines="6" .no-copy}
    NAME        ID-LINK                                         FSTYPE   SIZE MOUNTPOINT
    sda         usb-ST_16GB_AA6271026J1000000509-0:0                    14.9G
    ├─sda1      usb-ST_16GB_AA6271026J1000000509-0:0-part1                 1M
    ├─sda2      usb-ST_16GB_AA6271026J1000000509-0:0-part2      vfat     100M /boot
    └─sda3      usb-ST_16GB_AA6271026J1000000509-0:0-part3      ext4     2.9G /
    nvme0n1     nvme-eui.e8238fa6bf530001001b448b4aec2929              476.9G
    ├─nvme0n1p1 nvme-eui.e8238fa6bf530001001b448b4aec2929-part1 vfat     512M
    ├─nvme0n1p2 nvme-eui.e8238fa6bf530001001b448b4aec2929-part2 ext4   459.6G
    └─nvme0n1p3 nvme-eui.e8238fa6bf530001001b448b4aec2929-part3 swap    16.8G
    ```

    !!! Warning
        Make sure to copy the `ID-LINK` from toplevel disk device like `nvme0n1` or `sda` instead of `nvme0n1p1` or `sda1`


2. Edit the following fields inside the `./machines/jon/configuration.nix` and/or `./machines/sara/configuration.nix`

    <!-- Note: Use "jon" instead of "<machine>" as "<" is not supported in title tag -->
   ```nix title="./machines/jon/configuration.nix" hl_lines="13 18 22 26"
   {
      imports = [
        ./hardware-configuration.nix
        # contains your disk format and partitioning configuration.
        ../../modules/disko.nix
        # this file is shared among all machines
        ../../modules/shared.nix
        # enables GNOME desktop (optional)
        ../../modules/gnome.nix
      ];

      # Put your username here for login
      users.users.user.username = "__YOUR_USERNAME__";

      # Set this for clan commands that use ssh
      # If you change the hostname, you need to update this line to root@<new-hostname>
      # This only works however if you have avahi running on your admin machine else use IP
      clan.core.networking.targetHost = "root@__IP__";


      # Replace this __CHANGE_ME__ with the result of the lsblk command from step 1. 
      disko.devices.disk.main.device = "/dev/disk/by-id/__CHANGE_ME__";

      # IMPORTANT! Add your SSH key here
      # e.g. > cat ~/.ssh/id_ed25519.pub
      users.users.root.openssh.authorizedKeys.keys = [ "__YOUR_SSH_KEY__" ];

      # ...
   }
   ```


!!! Info "Replace `__YOUR_USERNAME__` with the ip of your machine, if you use avahi you can also use your hostname"
!!! Info "Replace `__IP__` with the ip of your machine, if you use avahi you can also use your hostname"
!!! Info "Replace `__CHANGE_ME__` with the appropriate `ID-LINK` identifier, such as `nvme-eui.e8238fa6bf530001001b448b4aec2929`"
!!! Info "Replace `__YOUR_SSH_KEY__` with your personal key, like `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILoMI0NC5eT9pHlQExrvR5ASV3iW9+BXwhfchq0smXUJ jon@jon-desktop`"


   You can also create additional machines using the cli:

   ```
   $ clan machines create <machinename>
   ```

### Step 2: Custom Disk Formatting

In `./modules/disko.nix`, a simple `ext4` disk partitioning scheme is defined for the Disko module. For more complex disk partitioning setups,
refer to the [Disko templates](https://github.com/nix-community/disko-templates) or  [Disko examples](https://github.com/nix-community/disko/tree/master/example).

### Step 3 (Optional): Renaming Machine

If you wish to name your machine to something else, do the following steps:

```
mv ./machines/jon/configuration.nix ./machines/newname/configuration.nix
```

Note that our clan lives inside a git repository.
Only files that have been added with `git add` are recognized by `nix`.
So for every file that you add or rename you also need to run:

```
git add ./path/to/my/file
```

For renaming jon to your own machine name, you can use the following command:

```
git mv ./machines/jon ./machines/newname
```

If you only want to setup a single machine at this point, you can delete `sara` from `flake.nix` as well as from the machines directory:

```
git rm -r ./machines/sara
```
