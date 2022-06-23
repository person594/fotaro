from datetime import datetime, timedelta, timezone
from typing import Any

"""

def escape(x: Any) -> str:
    if x is None:
        return "NULL"
    elif isinstance(x, str):
        return "'" + str_escape(x) + "'"
    elif isinstance(x, int):
        return str(x)
    else:
        return escape(repr(x))

def str_escape(s: str) -> str:
    return s.replace("'", "''")

def escape_identifier(s: str) -> str:
    return '"' + s.replace('"', '""') + '"'

"""

def now_timestamp() -> int:
    return utc_to_timestamp(datetime.now(timezone.utc))

def utc_to_timestamp(utc: datetime) -> int:
    return int((utc - datetime.fromtimestamp(0, timezone.utc)).total_seconds())

def timestamp_to_utc(timestamp: int) -> datetime:
    return datetime.fromtimestamp(timestamp, timezone.utc)

