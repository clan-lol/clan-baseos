
This guide provides an example setup for a single-disk ZFS system with native encryption, accessible for decryption remotely. 

!!! Warning
    This configuration only applies to `systemd-boot` enabled systems and **requires** UEFI booting.


Replace the highlighted lines with your own disk-id.
You can find our your disk-id by executing:
```bash
lsblk --output NAME,ID-LINK,FSTYPE,SIZE,MOUNTPOINT
```


=== "**Single Disk**"
    Below is the configuration for `disko.nix`
    ```nix hl_lines="14 40"
    { lib, ... }:
    let
    mirrorBoot = idx: {
        type = "disk";
        device = "/dev/disk/by-id/${idx}";
        content = {
            type = "gpt";
            partitions = {
                boot = {
                    size = "1M";
                    type = "EF02"; # for grub MBR
                    priority = 1;
                };
                ESP = lib.mkIf (idx == "nvme-eui.002538b931b59865") {
                    size = "1G";
                    type = "EF00";
                    content = {
                        type = "filesystem";
                        format = "vfat";
                        mountpoint = "/boot";
                        mountOptions = [ "nofail" ];
                    };
                };
                zfs = {
                    size = "100%";
                    content = {
                        type = "zfs";
                        pool = "zroot";
                    };
                };
            };
        };
    };
    in
    {
    boot.loader.systemd-boot.enable = true;

    disko.devices = {
        disk = {
            x = mirrorBoot "nvme-eui.002538b931b59865";
        };
        zpool = {
            zroot = {
                type = "zpool";
                rootFsOptions = {
                    compression = "lz4";
                    acltype = "posixacl";
                    xattr = "sa";
                    "com.sun:auto-snapshot" = "true";
                    mountpoint = "none";
                };
                datasets = {
                    "root" = {
                        type = "zfs_fs";
                        options = {
                            mountpoint = "none";
                            encryption = "aes-256-gcm";
                            keyformat = "passphrase";
                            keylocation = "file:///tmp/secret.key";
                        };
                    };
                    "root/nixos" = {
                        type = "zfs_fs";
                        options.mountpoint = "/";
                        mountpoint = "/";
                    };
                    "root/home" = {
                        type = "zfs_fs";
                        options.mountpoint = "/home";
                        mountpoint = "/home";
                    };
                    "root/tmp" = {
                        type = "zfs_fs";
                        mountpoint = "/tmp";
                        options = {
                            mountpoint = "/tmp";
                            sync = "disabled";
                        };
                    };
                };
            };
        };
    };
    }
    ```



=== "**Raid 1**"
    Below is the configuration for `disko.nix`
    ```nix hl_lines="14 40 41"
    { lib, ... }:
    let
    mirrorBoot = idx: {
        type = "disk";
        device = "/dev/disk/by-id/${idx}";
        content = {
            type = "gpt";
            partitions = {
                boot = {
                    size = "1M";
                    type = "EF02"; # for grub MBR
                    priority = 1;
                };
                ESP = lib.mkIf (idx == "nvme-eui.002538b931b59865") {
                    size = "1G";
                    type = "EF00";
                    content = {
                        type = "filesystem";
                        format = "vfat";
                        mountpoint = "/boot";
                        mountOptions = [ "nofail" ];
                    };
                };
                zfs = {
                    size = "100%";
                    content = {
                        type = "zfs";
                        pool = "zroot";
                    };
                };
            };
        };
    };
    in
    {
    boot.loader.systemd-boot.enable = true;

    disko.devices = {
        disk = {
            x = mirrorBoot "nvme-eui.002538b931b59865";
            y = mirrorBoot "myOtherDrive"
        };
        zpool = {
            zroot = {
                type = "zpool";
                rootFsOptions = {
                    compression = "lz4";
                    acltype = "posixacl";
                    xattr = "sa";
                    "com.sun:auto-snapshot" = "true";
                    mountpoint = "none";
                };
                datasets = {
                    "root" = {
                        type = "zfs_fs";
                        options = {
                            mountpoint = "none";
                            encryption = "aes-256-gcm";
                            keyformat = "passphrase";
                            keylocation = "file:///tmp/secret.key";
                        };
                    };
                    "root/nixos" = {
                        type = "zfs_fs";
                        options.mountpoint = "/";
                        mountpoint = "/";
                    };
                    "root/home" = {
                        type = "zfs_fs";
                        options.mountpoint = "/home";
                        mountpoint = "/home";
                    };
                    "root/tmp" = {
                        type = "zfs_fs";
                        mountpoint = "/tmp";
                        options = {
                            mountpoint = "/tmp";
                            sync = "disabled";
                        };
                    };
                };
            };
        };
    };
    }
    ```

Below is the configuration for `initrd.nix`.  
Replace `<yourkey>` with your ssh public key.  
Replace `kernelModules` with the ethernet module loaded one on your target machine.
```nix hl_lines="18 29"
{config, pkgs, ...}:

{

  boot.initrd.systemd = {
    enable = true;
  };

  # uncomment this if you want to be asked for the decryption password on login
  #users.root.shell = "/bin/systemd-tty-ask-password-agent";

  boot.initrd.network = {
    enable = true;

    ssh = {
      enable = true;
      port = 7172;
      authorizedKeys = [ "<yourkey>" ];
      hostKeys = [
        "/var/lib/initrd-ssh-key"
      ];
    };
  };
  boot.initrd.availableKernelModules = [
    "xhci_pci"
  ];

  # Find out the required network card driver by running `lspci -k` on the target machine
  boot.initrd.kernelModules = [ "r8169" ]; 
}
```


### Step 1: Copying SSH Public Key

Before starting the installation process, ensure that the SSH public key is copied to the NixOS installer.

1. Copy your public SSH key to the installer, if it has not been copied already:

```bash
ssh-copy-id -o PreferredAuthentications=password -o PubkeyAuthentication=no root@nixos-installer.local
```

### Step 1.5: Prepare Secret Key and Clear Disk Data

1. Access the installer using SSH:

```bash
ssh root@nixos-installer.local
```

2. Create a `secret.key` file in `/tmp` using `nano` or another text editor:

```bash
nano /tmp/secret.key
```

3. Discard the old disk partition data:

```bash
blkdiscard /dev/disk/by-id/nvme-eui.002538b931b59865
```

4. Run the `clan` machine installation with the following command:

```bash
clan machines install gchq-local root@nixos-installer --yes --no-reboot
```

### Step 2: ZFS Pool Import and System Installation

1. SSH into the installer once again:

```bash
ssh root@nixos-installer.local
```

2. Perform the following commands on the remote installation environment:

```bash
zpool import zroot
zfs set keystate=prompt zroot/root
zfs load-key zroot/root
zfs set mountpoint=/mnt zroot/root/nixos
mount /dev/nvme0n1p2 /mnt/boot
```

3. Disconnect from the SSH session:

```bash
CTRL+D
```

4. Securely copy your local `initrd_rsa_key` to the installer's `/mnt` directory:

```bash
scp ~/.ssh/initrd_rsa_key root@nixos-installer.local:/mnt/var/lib/initrd-ssh-key
```

5. SSH back into the installer:

```bash
ssh root@nixos-installer.local
```

6. Navigate to the `/mnt` directory, enter the `nixos-enter` environment, and then exit:

```bash
cd /mnt
nixos-enter
realpath /run/current-system
exit
```

7. Run the `nixos-install` command with the appropriate system path `<SYS_PATH>`:

```bash
nixos-install --no-root-passwd --no-channel-copy --root /mnt --system <SYS_PATH>
```

8. After the installation process, unmount `/mnt/boot`, change the ZFS mountpoint, and reboot the system:

```bash
umount /mnt/boot
cd /
zfs set mountpoint=/ zroot/root/nixos
reboot
```

9. Perform a hard reboot of the machine and remove the USB stick.

### Step 3: Accessing the Initial Ramdisk (initrd) Environment

1. SSH into the initrd environment using the `initrd_rsa_key` and provided port:

```bash
ssh -p 7172 root@192.168.178.141
```

2. Run the `systemd-tty-ask-password-agent` utility to query a password:

```bash
systemd-tty-ask-password-agent --query
```

After completing these steps, your NixOS should be successfully installed and ready for use.

**Note:** Replace `root@nixos-installer.local` and `192.168.178.141` with the appropriate user and IP addresses for your setup. Also, adjust `<SYS_PATH>` to reflect the correct system path for your environment.
