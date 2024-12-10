# Hardware Installation

For installations on physical hardware, create a NixOS installer image and transfer it to a bootable USB drive as described below.

## Creating a Bootable USB Drive on Linux

To create a bootable USB flash drive with the NixOS installer:

### Download the install iso

Either with wget:

```shellSession
wget https://github.com/nix-community/nixos-images/releases/download/nixos-unstable/nixos-installer-x86_64-linux.iso
```

or with curl:

```shellSession
curl -L https://github.com/nix-community/nixos-images/releases/download/nixos-unstable/nixos-installer-x86_64-linux.iso -o nixos-installer-x86_64-linux.iso
```

### Prepare the USB Flash Drive

1. Insert your USB flash drive into your computer.

2. Identify your flash drive with `lsblk`.

    ```shellSession
    lsblk
    NAME                                          MAJ:MIN RM   SIZE RO TYPE  MOUNTPOINTS
    sdb                                             8:0    1 117,2G  0 disk
    └─sdb1                                          8:1    1 117,2G  0 part  /run/media/qubasa/INTENSO
    nvme0n1                                       259:0    0   1,8T  0 disk
    ├─nvme0n1p1                                   259:1    0   512M  0 part  /boot
    └─nvme0n1p2                                   259:2    0   1,8T  0 part
      └─luks-f7600028-9d83-4967-84bc-dd2f498bc486 254:0    0   1,8T  0 crypt /nix/store
    ```

    In this case it's `sdb`

3. Ensure all partitions on the drive are unmounted. Replace `sdX` in the command below with your device identifier (like `sdb`, etc.):

    ```shellSession
    sudo umount /dev/sdb1
    ```

### Write the Image to the USB Drive

Use the `dd` utility to write the NixOS installer image to your USB drive:

  ```shellSession
  sudo dd bs=4M conv=fsync oflag=direct status=progress if=./nixos-installer-x86_64-linux.iso of=/dev/sd<X>
  ```

  In this case, the USB device is `sdb` use `of=/dev/sdb`

### Boot and Connect

After writing the installer to the USB drive, use it to boot the target machine.

1. For this secure boot needs to be disabled. Go into your UEFI / Bios settings by pressing one of the keys outlined below while booting:

   - **Dell**: F2/Del (BIOS Setup)
   - **HP**: Esc (Startup Menu)
   - **Lenovo**: F2/Fn+F2/Novo Button (IdeaPad Boot Menu/BIOS Setup)
   - **Acer**: F2/Del (BIOS Setup)
   - **Asus**: F2/Del (BIOS Setup)
   - **Toshiba**: Esc then F12 (Alternate Method)
   - **Sony**: F11
   - **Samsung**: F2 (BIOS Setup)
   - **MSI**: Del (BIOS Setup)
   - **Apple**: Option (Alt) Key (Boot Menu for Mac)
   - If your hardware was not listed read the manufacturers instructions how to enter the boot Menu/BIOS Setup.

2. Inside the UEFI/Bios Menu go to `Security->Secure Boot` and disable secure boot

3. Save your settings. Put in the USB stick and reboot.

4. Press one of keys outlined below to go into the Boot Menu

       - **Dell**: F12 (Boot Menu)
       - **HP**: F9 (Boot Menu)
       - **Lenovo**: F12 (ThinkPad Boot Menu)
       - **Acer**: F12 (Boot Menu)
       - **Asus**: F8/Esc (Boot Menu)
       - **Toshiba**: F12/F2 (Boot Menu)
       - **Sony**: F11
       - **Samsung**: F2/F12/Esc (Boot Menu)
       - **MSI**: F11
       - **Apple**: Option (Alt) Key (Boot Menu for Mac)
       - If your hardware was not listed read the manufacturers instructions how to enter the boot Menu/BIOS Setup.


5. Select `NixOS` to boot into the clan installer

6. The installer will display an IP address and a root password, which you can use to connect via SSH.
    Alternatively you can also use the displayed QR code.

7. Set your keyboard language (i.e. `de` for German keyboards, default is English). Important for writing passwords correctly.

    ```shellSession
    loadkeys de
    ```

8. If you only have Wifi available, execute:

    1. Bring up the `iwd` shell

        ```shellSession
        iwctl
        ```

    2. List available networks. Double press tab after station for autocompleting your wlan device. In this case `wlan0`

        ```shellSession
        [iwd] station wlan0 get-networks
        ```

    3. Connect to a Wifi network. Replace `SSID` with the wlan network name.

        ```shellSession
        [iwd] station wlan0 connect SSID
        ```

9. Now that you have internet re-execute the init script by pressing `Ctrl+D` or by executing:

    ```shellSession
    bash
    ```

10. Connect to the machine over ssh

    ```shellSession
    ssh-copy-id -o PreferredAuthentications=password root@<ip>
    ```

    Use the root password displayed on your screen as login.

---

# What's next?

- Deploy a clan machine-configuration on your prepared machine

---
