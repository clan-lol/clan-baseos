#!/usr/bin/env bash

# Read 16 bytes from /dev/urandom
uuid=$(dd if=/dev/urandom bs=1 count=16 2>/dev/null | od -An -tx1 | tr -d ' \n')

# Break the UUID into pieces and apply the required modifications
byte6=${uuid:12:2}
byte8=${uuid:16:2}

# Construct the correct version and variant
hex_byte6=$(printf "%x" $((0x$byte6 & 0x0F | 0x40)))
hex_byte8=$(printf "%x" $((0x$byte8 & 0x3F | 0x80)))

# Rebuild the UUID with the correct fields
uuid_v4="${uuid:0:12}${hex_byte6}${uuid:14:2}${hex_byte8}${uuid:18:14}"

# Format the UUID correctly 8-4-4-4-12
uuid_formatted="${uuid_v4:0:8}-${uuid_v4:8:4}-${uuid_v4:12:4}-${uuid_v4:16:4}-${uuid_v4:20:12}"

echo -n "$uuid_formatted"