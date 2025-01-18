# Introduction to Backups

When you're managing your own services, creating regular backups is crucial to ensure your data's safety.
This guide introduces you to Clan's built-in backup functionalities.
Clan supports backing up your data to both local storage devices (like USB drives) and remote servers, using well-known tools like borgbackup and rsnapshot.
We might add more options in the future, but for now, let's dive into how you can secure your data.

## Backing Up Locally with Localbackup

Localbackup lets you backup your data onto physical storage devices connected to your computer,
such as USB hard drives or network-attached storage. It uses a tool called rsnapshot for this purpose.

### Setting Up Localbackup

1. **Identify Your Backup Device:**

First, figure out which device you'll use for backups. You can see all connected devices by running this command in your terminal:

```bash
lsblk --output NAME,PTUUID,FSTYPE,SIZE,MOUNTPOINT
```

Look for the device you intend to use for backups and note its details.

2. **Configure Your Backup Device:**

Once you've identified your device, you'll need to add it to your configuration.
Here's an example NixOS configuration for a device located at `/dev/sda2` with an `ext4` filesystem:

```nix
{
  fileSystems."/mnt/hdd" = {
    device = "/dev/sda2";
    fsType = "ext4";
    options = [ "defaults" "noauto" ];
  };
}
```

Replace `/dev/sda2` with your device and `/mnt/hdd` with your preferred mount point.

3. **Set Backup Targets:** Next, define where on your device you'd like the backups to be stored:

   ```nix
   {
     clan.localbackup.targets.hdd = {
       directory = "/mnt/hdd/backup";
       mountpoint = "/mnt/hdd";
     };
   }
   ```

   Change `/mnt/hdd` to the actual mount point you're using.

4. **Create Backups:** To create a backup, run:

   ```bash
   clan backups create mymachine
   ```

   This command saves snapshots of your data onto the backup device.

5. **Listing Backups:** To see available backups, run:

  ```bash
  clan backups list mymachine
  ```

## Remote Backups with Borgbackup

### Overview of Borgbackup

Borgbackup splits the backup process into two parts: a backup client that sends data to a backup server.
The server stores the backups.

### Setting Up the Borgbackup Client

1. **Specify Backup Server:**

Start by indicating where your backup data should be sent. Replace `hostname` with your server's address:

```nix
{
  clan.borgbackup.destinations = {
    myhostname = {
      repo = "borg@backuphost:/var/lib/borgbackup/myhostname";
    };
  };
}
```

2. **Select Folders to Backup:**

Decide which folders you want to back up. For example, to backup your home and root directories:

```nix
{ clan.core.state.userdata.folders = [ "/home" "/root" ]; }
```

3. **Generate Backup Credentials:**

Run `clan facts generate <yourmachine>` to prepare your machine for backup, creating necessary SSH keys and credentials.

### Setting Up the Borgbackup Server

1. **Configure Backup Repository:**

On the server where backups will be stored, enable the SSH daemon and set up a repository for each client:

```nix
{
  services.borgbackup.repos.myhostname = {
    path = "/var/lib/borgbackup/myhostname";
    authorizedKeys = [
      (builtins.readFile  (config.clan.core.settings.directory + "/machines/myhostname/facts/borgbackup.ssh.pub"))
    ];
  };
}
```

Ensure the path to the public key is correct.

2. **Update Your Systems:** Apply your changes by running `clan machines update` to both the server and your client

### Managing Backups

- **Scheduled Backups:**

  Backups are automatically performed nightly. To check the next scheduled backup, use:

  ```bash
  systemctl list-timers | grep -E 'NEXT|borg'
  ```

- **Listing Backups:** To see available backups, run:

  ```bash
  clan backups list mymachine
  ```

- **Manual Backups:** You can also initiate a backup manually:

  ```bash
  clan backups create mymachine
  ```
