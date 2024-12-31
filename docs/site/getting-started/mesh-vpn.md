# Mesh VPN

This guide provides detailed instructions for configuring
[ZeroTier VPN](https://zerotier.com) within Clan. Follow the
outlined steps to set up a machine as a VPN controller (`<CONTROLLER>`) and to
include a new machine into the VPN.

## Concept

By default all machines within one clan are connected via a chosen network technology.

```{.no-copy}
Clan
    Node A
    <-> (zerotier / mycelium / ...)
    Node B
```

If you select multiple network technologies at the same time. e.g. (zerotier + yggdrassil)
You must choose one of them as primary network and the machines are always connected via the primary network.

## 1. Set-Up the VPN Controller

The VPN controller is initially essential for providing configuration to new
peers. Once addresses are allocated, the controller's continuous operation is not essential.

1. **Designate a Machine**: Label a machine as the VPN controller in the clan,
   referred to as `<CONTROLLER>` henceforth in this guide.
2. **Add Configuration**: Input the following configuration to the NixOS
   configuration of the controller machine:
   ```nix
   clan.core.networking.zerotier.controller = {
     enable = true;
     public = true;
   };
   ```
3. **Update the Controller Machine**: Execute the following:
   ```bash
   clan machines update <CONTROLLER>
   ```
   Your machine is now operational as the VPN controller.

## 2. Add Machines to the VPN

To introduce a new machine to the VPN, adhere to the following steps:

1. **Update Configuration**: On the new machine, incorporate the following to its
   configuration, substituting `<CONTROLLER>` with the controller machine name:
   ```nix
   { config, ... }: {
     clan.core.networking.zerotier.networkId = builtins.readFile (config.clan.core.settings.directory + "/machines/<CONTROLLER>/facts/zerotier-network-id");
   }
   ```
1. **Update the New Machine**: Execute:
   ```bash
   $ clan machines update <NEW_MACHINE>
   ```
   Replace `<NEW_MACHINE>` with the designated new machine name.

    !!! Note "For Private Networks"
        1. **Retrieve Zerotier Metadata**

            === "From the repo"
                **Retrieve the ZeroTier IP**: In the clan repo, execute:
                 ```console
                 $ clan facts list <NEW_MACHINE> |  jq -r '.["zerotier-ip"]'
                 ```

                 The returned address is the Zerotier IP address of the machine.

            === "On the new machine"
                **Retrieve the ZeroTier ID**: On the `new_machine`, execute:
                 ```bash
                 $ sudo zerotier-cli info
                 ```
                 Example Output:
                 ```{.console, .no-copy}
                 200 info d2c71971db 1.12.1 OFFLINE
                 ```
                 , where `d2c71971db` is the ZeroTier ID.


        2. **Authorize the New Machine on the Controller**: On the controller machine,
             execute:

            === "with ZerotierIP"
                 ```bash
                 $ sudo zerotier-members allow --member-ip <IP>
                 ```
                 Substitute `<IP>` with the ZeroTier IP obtained previously.
            === "with ZerotierID"
                 ```bash
                 $ sudo zerotier-members allow <ID>
                 ```
                 Substitute `<ID>` with the ZeroTier ID obtained previously.

2. **Verify Connection**: On the `new_machine`, re-execute:
   ```bash
   $ sudo zerotier-cli info
   ```
   The status should now be "ONLINE":
   ```{.console, .no-copy}
   200 info d2c71971db 1.12.1 ONLINE
   ```

!!! success "Congratulations!"
    The new machine is now part of the VPN, and the ZeroTier
    configuration on NixOS within the Clan project is complete.

## Further

Currently you can only use **Zerotier** as networking technology because this is the first network stack we aim to support.
In the future we plan to add additional network technologies like tinc, head/tailscale, yggdrassil and mycelium.

We chose zerotier because in our tests it was a straight forwards solution to bootstrap.
It allows you to selfhost a controller and the controller doesn't need to be globally reachable.
Which made it a good fit for starting the project.
