---
description = "Configures [Zerotier VPN](https://zerotier.com) secure and efficient networking within a Clan.."
features = [ "inventory" ]
---

## Overview

This guide explains how to set up and manage a [ZeroTier VPN](https://zerotier.com) for a clan network. Each VPN requires a single controller and can support multiple peers and optional moons for better connectivity.

## Roles

### 1. Controller

The [Controller](https://docs.zerotier.com/controller/) manages network membership and is responsible for admitting new peers.
When a new node is added to the clan, the controller must be updated to ensure it has the latest member list.

- **Key Points:**
  - Must be online to admit new machines to the VPN.
  - Existing nodes can continue to communicate even when the controller is offline.

### 2. Moons

[Moons](https://docs.zerotier.com/roots) act as relay nodes,
providing direct connectivity to peers via their public IP addresses.
They enable devices that are not publicly reachable to join the VPN by routing through these nodes.

- **Configuration Notes:**
  - Each moon must define its public IP address.
  - Ensures connectivity for devices behind NAT or restrictive firewalls.

### 3. Peers

Peers are standard nodes in the VPN.
They connect to other peers, moons, and the controller as needed.

- **Purpose:**
  - General role for all machines that are neither controllers nor moons.
  - Ideal for most clan members' devices.
