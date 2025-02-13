
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
    ```nix hl_lines="13 53"
      --8<-- "docs/code-examples/disko-single-disk.nix"
    ```



=== "**Raid 1**"
    Below is the configuration for `disko.nix`
    ```nix hl_lines="13 53 54"
      --8<-- "docs/code-examples/disko-raid.nix"
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
        "/var/lib/initrd_host_ed25519_key"
        "/var/lib/initrd_host_rsa_key"
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

### Step 1.5: Prepare Secret Key and Partition Disks

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
blkdiscard /dev/disk/by-id/<installdisk>
```

4. Run `clan` machines install, only running kexec and disko, with the following command:

```bash
clan machines install gchq-local --target-host root@nixos-installer --phases kexec,disko
```

### Step 2: ZFS Pool Import and System Installation

1. SSH into the installer once again:

```bash
ssh root@nixos-installer.local
```

2. Run the following command on the remote installation environment:

```bash
zfs set keylocation=prompt zroot/root
```

3. Disconnect from the SSH session:

```bash
CTRL+D
```

4. Locally generate ssh host keys. You only need to generate ones for the algorithms you're using in `authorizedKeys`.

```bash
ssh-keygen -q -N "" -t ed25519 -f ./initrd_host_ed25519_key
ssh-keygen -q -N "" -t rsa -b 4096 -f ./initrd_host_rsa_key
```

5. Securely copy your local initrd ssh host keys to the installer's `/mnt` directory:

```bash
scp ./initrd_host* root@nixos-installer.local:/mnt/var/lib/
```

6. Install nixos to the mounted partitions
```bash
clan machines install gchq-local --target-host root@nixos-installer --phases install
```

7. After the installation process, unmount `/mnt/boot`, change the ZFS mountpoints and unmount all the ZFS volumes by exporting the zpool:

```bash
umount /mnt/boot
cd /
zfs set -u mountpoint=/ zroot/root/nixos
zfs set -u mountpoint=/tmp zroot/root/tmp
zfs set -u mountpoint=/home zroot/root/home
zpool export zroot
```

8. Perform a reboot of the machine and remove the USB installer.

### Step 3: Accessing the Initial Ramdisk (initrd) Environment

1. SSH into the initrd environment using the `initrd_rsa_key` and provided port:

```bash
ssh -p 7172 root@192.168.178.141
```

2. Run the `systemd-tty-ask-password-agent` utility to query a password:

```bash
systemd-tty-ask-password-agent
```

After completing these steps, your NixOS should be successfully installed and ready for use.

**Note:** Replace `root@nixos-installer.local` and `192.168.178.141` with the appropriate user and IP addresses for your setup. Also, adjust `<SYS_PATH>` to reflect the correct system path for your environment.
