At the moment, NixOS/Clan does not support [Secure Boot](https://wiki.gentoo.org/wiki/Secure_Boot). Therefore, you need to disable it in the BIOS. You can watch this [video guide](https://www.youtube.com/watch?v=BKVShiMUePc) or follow the instructions below:

### Step 1: Insert the USB Stick
- Begin by inserting the USB stick into a USB port on your computer.

### Step 2: Access the UEFI/BIOS Menu
- Restart your computer.
- As your computer restarts, press the appropriate key to enter the UEFI/BIOS settings. 
??? tip "The key depends on your laptop or motherboard manufacturer. Click to see a reference list:"

    | Manufacturer       | UEFI/BIOS Key(s)          |
    |--------------------|---------------------------|
    | ASUS               | `Del`, `F2`               |
    | MSI                | `Del`, `F2`               |
    | Gigabyte           | `Del`, `F2`               |
    | ASRock             | `Del`, `F2`               |
    | Lenovo             | `F1`, `F2`, `Enter` (alternatively `Fn + F2`) |
    | HP                 | `Esc`, `F10`              |
    | Dell               | `F2`, `Fn + F2`, `Esc`    |
    | Acer               | `F2`, `Del`               |
    | Samsung            | `F2`, `F10`               |
    | Toshiba            | `F2`, `Esc`               |
    | Sony               | `F2`, `Assist` button     |
    | Fujitsu            | `F2`                      |
    | Microsoft Surface  | `Volume Up` + `Power`     |
    | IBM/Lenovo ThinkPad| `Enter`, `F1`, `F12`      |
    | Biostar            | `Del`                     |
    | Zotac              | `Del`, `F2`               |
    | EVGA               | `Del`                     |
    | Origin PC          | `F2`, `Delete`            |

    !!! Note
        Pressing the key quickly and repeatedly is sometimes necessary to access the UEFI/BIOS menu, as the window to enter this mode is brief.

### Step 3: Access Advanced Mode (Optional)
- If your UEFI/BIOS has a `Simple` or `Easy` mode interface, look for an option labeled `Advanced Mode` (often found in the lower right corner).
- Click on `Advanced Mode` to access more settings. This step is optional, as your boot settings might be available in the basic view.

### Step 4: Disable Secure Boot
- Locate the `Secure Boot` option in your UEFI/BIOS settings. This is typically found under a `Security` tab, `Boot` tab, or a similarly named section.
- Set the `Secure Boot` option to `Disabled`.

### Step 5: Change Boot Order
- Find the option to adjust the boot order—often labeled `Boot Order`, `Boot Sequence`, or `Boot Priority`.
- Ensure that your USB device is set as the first boot option. This allows your computer to boot from the USB stick.

### Step 6: Save and Exit
- Save your changes before exiting the UEFI/BIOS menu. Look for a `Save & Exit` option or press the corresponding function key (often `F10`).
- Your computer should now restart and boot from the USB stick.
