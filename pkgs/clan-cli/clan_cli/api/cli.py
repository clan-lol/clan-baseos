#!/usr/bin/env python3

import argparse
import json

from . import API

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Debug the API.")
    args = parser.parse_args()

    schema = API.to_json_schema()
    print(json.dumps(schema, indent=4))
