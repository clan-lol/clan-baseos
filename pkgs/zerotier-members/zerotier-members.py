#!/usr/bin/env python
import argparse
import http.client
import ipaddress
import json
import sys
from pathlib import Path

ZEROTIER_STATE_DIR = Path("/var/lib/zerotier-one")


class ClanError(Exception):
    pass


def compute_zerotier_ip(network_id: str, identity: str) -> ipaddress.IPv6Address:
    assert (
        len(network_id) == 16
    ), "network_id must be 16 characters long, got {network_id}"
    nwid = int(network_id, 16)
    node_id = int(identity, 16)
    addr_parts = bytearray(
        [
            0xFD,
            (nwid >> 56) & 0xFF,
            (nwid >> 48) & 0xFF,
            (nwid >> 40) & 0xFF,
            (nwid >> 32) & 0xFF,
            (nwid >> 24) & 0xFF,
            (nwid >> 16) & 0xFF,
            (nwid >> 8) & 0xFF,
            (nwid) & 0xFF,
            0x99,
            0x93,
            (node_id >> 32) & 0xFF,
            (node_id >> 24) & 0xFF,
            (node_id >> 16) & 0xFF,
            (node_id >> 8) & 0xFF,
            (node_id) & 0xFF,
        ]
    )
    return ipaddress.IPv6Address(bytes(addr_parts))


def compute_member_id(ipv6_addr: str) -> str:
    addr = ipaddress.IPv6Address(ipv6_addr)
    addr_bytes = bytearray(addr.packed)

    # Extract the bytes corresponding to the member_id (node_id)
    node_id_bytes = addr_bytes[10:16]
    node_id = int.from_bytes(node_id_bytes, byteorder="big")

    member_id = format(node_id, "x").zfill(10)[-10:]

    return member_id


# this is managed by the nixos module
def get_network_id() -> str:
    p = Path("/etc/zerotier/network-id")
    if not p.exists():
        msg = f"{p} file not found. Have you enabled the zerotier controller on this host?"
        raise ClanError(msg)
    return p.read_text().strip()


def allow_member(args: argparse.Namespace) -> None:
    if args.member_ip:
        member_id = compute_member_id(args.member_id)
    else:
        member_id = args.member_id
    network_id = get_network_id()
    token = ZEROTIER_STATE_DIR.joinpath("authtoken.secret").read_text()
    conn = http.client.HTTPConnection("localhost", 9993)
    conn.request(
        "POST",
        f"/controller/network/{network_id}/member/{member_id}",
        '{"authorized": true}',
        {"X-ZT1-AUTH": token},
    )
    resp = conn.getresponse()
    if resp.status != 200:
        msg = f"the zerotier daemon returned this error: {resp.status} {resp.reason}"
        raise ClanError(msg)
    print(resp.status, resp.reason)


def list_members(args: argparse.Namespace) -> None:
    network_id = get_network_id()
    networks = ZEROTIER_STATE_DIR / "controller.d" / "network" / network_id / "member"
    if not networks.exists():
        return
    for member in networks.iterdir():
        with member.open() as f:
            data = json.load(f)
            try:
                member_id = data["id"]
            except KeyError as e:
                msg = f"error: {member} does not contain an id"
                raise ClanError(msg) from e
            print(
                member_id,
                compute_zerotier_ip(network_id, data["id"]),
                data["authorized"] or "false",
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(dest="command")
    parser_allow = subparser.add_parser("allow", help="Allow a member to join")
    parser_allow.add_argument(
        "--member-ip",
        help="Allow a member to join by their zerotier ipv6 address",
        action="store_true",
    )
    parser_allow.add_argument("member_id")
    parser_allow.set_defaults(func=allow_member)

    parser_list = subparser.add_parser("list", help="List members")
    parser_list.set_defaults(func=list_members)

    args = parser.parse_args()
    try:
        args.func(args)
    except ClanError as e:
        print(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
