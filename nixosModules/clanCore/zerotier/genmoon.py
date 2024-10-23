#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile


def main() -> None:
    if len(sys.argv) != 4:
        print("Usage: genmoon.py <moon.json> <endpoint.json> <moons.d>")
        sys.exit(1)
    moon_json = sys.argv[1]
    endpoint_config = sys.argv[2]
    moons_d = sys.argv[3]

    moon_json = json.loads(Path(moon_json).read_text())
    moon_json["roots"][0]["stableEndpoints"] = json.loads(
        Path(endpoint_config).read_text()
    )

    with NamedTemporaryFile("w") as f:
        f.write(json.dumps(moon_json))
        f.flush()
        Path(moons_d).mkdir(parents=True, exist_ok=True)
        subprocess.run(["zerotier-idtool", "genmoon", f.name], cwd=moons_d, check=True)


if __name__ == "__main__":
    main()
