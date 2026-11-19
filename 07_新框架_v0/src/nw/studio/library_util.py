"""Small serialization helpers shared by the independent library services."""
from datetime import datetime, timezone
import json


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def encode(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)
