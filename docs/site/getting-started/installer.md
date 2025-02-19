# Clan Installer Image for Physical Machines

To install Clan on physical machines, you need to use our custom installer image. This is necessary for proper installation and operation.

!!! note "Using a Cloud VM?"
    If you're using a cloud provider's virtual machine (VM), you can skip this section and go directly to the [Configure Machines](configure.md) step. In this scenario, we automatically use [nixos-anywhere](https://github.com/nix-community/nixos-anywhere) to replace the kernel during runtime.

??? info "Why nixos-anywhere Doesn't Work on Physical Hardware?"
    nixos-anywhere relies on [kexec](https://wiki.archlinux.org/title/Kexec) to replace the running kernel with our custom one. This method often has compatibility issues with real hardware, especially systems with dedicated graphics cards like laptops and servers, leading to crashes and black screens.

??? info "Reasons for a Custom Install Image"
    Our custom install images are built to include essential tools like [nixos-facter](https://github.com/nix-community/nixos-facter) and support for [ZFS](https://wiki.archlinux.org/title/ZFS). They're also optimized to run on systems with as little as 1 GB of RAM, ensuring efficient performance even on lower-end hardware.


### Step 0. Prerequisites

- [x] A free USB Drive with at least 1.5GB (All data on it will be lost)
- [x] Linux/NixOS Machine with Internet

### Step 1. Identify the USB Flash Drive

1. Insert your USB flash drive into your computer.

2. Identify your flash drive with `lsblk`:

    ```shellSession
    lsblk
    ```

    ```{.shellSession hl_lines="2" .no-copy}
    NAME                                          MAJ:MIN RM   SIZE RO TYPE  MOUNTPOINTS
    sdb                                             8:0    1 117,2G  0 disk
    └─sdb1                                          8:1    1 117,2G  0 part  /run/media/qubasa/INTENSO
    nvme0n1                                       259:0    0   1,8T  0 disk
    ├─nvme0n1p1                                   259:1    0   512M  0 part  /boot
    └─nvme0n1p2                                   259:2    0   1,8T  0 part
      └─luks-f7600028-9d83-4967-84bc-dd2f498bc486 254:0    0   1,8T  0 crypt /nix/store
    ```

    !!! Info "In this case the USB device is `sdb`"

3. Ensure all partitions on the drive are unmounted. Replace `sdb1` in the command below with your device identifier (like `sdc1`, etc.):

```shellSession
sudo umount /dev/sdb1
```
=== "**Linux OS**"
    ### Step 2. Create a Custom Installer

    Using clan flash enables the inclusion of ssh public keys into the image.
    It also allows to set language and keymap in the installer image.

    ```bash
    clan flash write --flake git+https://git.clan.lol/clan/clan-core \
      --ssh-pubkey $HOME/.ssh/id_ed25519.pub \
      --keymap us \
      --language en_US.UTF-8 \
      --disk main /dev/sd<X> \
      flash-installer
    ```
    !!! Note
        Replace `$HOME/.ssh/id_ed25519.pub` with a path to your SSH public key.
        Replace `/dev/sd<X>` with the drive path you want to flash

    !!! Danger "Specifying the wrong device can lead to unrecoverable data loss."

        The `clan flash` utility will erase the disk. Make sure to specify the correct device

    - **SSH-Pubkey Option**

        To add an ssh public key into the installer image append the option:
        ```
        --ssh-pubkey <pubkey_path>
        ```
        If you do not have an ssh key yet, you can generate one with `ssh-keygen -t ed25519` command.
        This ssh key will be installed into the root user.

    - **Connect to the installer**

        On boot, the installer will display on-screen the IP address it received from the network.
        If you need to configure Wi-Fi first, refer to the next section.
        If Multicast-DNS (Avahi) is enabled on your own machine, you can also access the installer using the `flash-installer.local` address.

    - **List Keymaps**

        You can get a list of all keymaps with the following command:
        ```
        clan flash list keymaps
        ```

    - **List Languages**

        You can get a list of all languages with the following command:
        ```
        clan flash list languages
        ```




=== "**Other OS**"
    ### Step 2. Download Generic Installer

    For x86_64:

    ```shellSession
    wget https://github.com/nix-community/nixos-images/releases/download/nixos-unstable/nixos-installer-x86_64-linux.iso
    ```

    For generic arm64 / aarch64 (probably does not work on raspberry pi...)

    ```shellSession
    wget https://github.com/nix-community/nixos-images/releases/download/nixos-unstable/nixos-installer-aarch64-linux.iso
    ```

    !!! Note
        If you don't have `wget` installed, you can use `curl --progress-bar -OL <url>` instead.

    ### Step 2.5 Flash the Installer to the USB Drive

    !!! Danger "Specifying the wrong device can lead to unrecoverable data loss."

        The `dd` utility will erase the disk. Make sure to specify the correct device (`of=...`)

        For example if the USB device is `sdb` use `of=/dev/sdb` (on macOS it will look more like /dev/disk1)

    On Linux, you can use the `lsblk` utility to identify the correct disko

    ```
    lsblk --output NAME,ID-LINK,FSTYPE,SIZE,MOUNTPOINT
    ```

    On macos use `diskutil`:

    ```
    diskutil list
    ```

    Use the `dd` utility to write the NixOS installer image to your USB drive.
    Replace `/dev/sd<X>` with your external drive from above.

    ```shellSession
    sudo dd bs=4M conv=fsync status=progress if=./nixos-installer-x86_64-linux.iso of=/dev/sd<X>
    ```

    - **Connect to the installer

      On boot, the installer will display on-screen the IP address it received from the network.
      If you need to configure Wi-Fi first, refer to the next section.
      If Multicast-DNS (Avahi) is enabled on your own machine, you can also access the installer using the `nixos-installer.local` address.


###  Step 3: Boot From USB Stick
- To use, boot from the Clan USB drive with **secure boot turned off**. For step by step instructions go to [Disabling Secure Boot](../manual/secure-boot.md)


## (Optional) Connect to Wifi Manually

If you don't have access via LAN the Installer offers support for connecting via Wifi.

```shellSession
iwctl
```

This will enter `iwd`

```{.console, .no-copy}
[iwd]#
```

Now run the following command to connect to your Wifi:

```{.shellSession .no-copy}
# Identify your network device.
device list

# Replace 'wlan0' with your wireless device name
# Find your Wifi SSID.
station wlan0 scan
station wlan0 get-networks

# Replace your_ssid with the Wifi SSID
# Connect to your network.
station wlan0 connect your_ssid

# Verify you are connected
station wlan0 show
```

If the connection was successful you should see something like this:

```{.console, .no-copy}
State                 connected
Connected network     FRITZ!Box (Your router device)
IPv4 address          192.168.188.50 (Your new local ip)
```

Press ++ctrl+d++ to exit `IWD`.

!!! Important
    Press ++ctrl+d++ **again** to update the displayed QR code and connection information.

You're all set up

