import dataclasses
import json
from typing import Any


class ClanJSONEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        # Check if the object has a to_json method
        if hasattr(o, "to_json") and callable(o.to_json):
            return o.to_json()
        # Check if the object is a dataclass
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        # Otherwise, use the default serialization
        return super().default(o)
