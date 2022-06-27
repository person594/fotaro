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



def unflatten_dict(d, delimiter='.'):
    print(d)
    unflattened = {}
    for k, v in d.items():
        if isinstance(v, dict):
            unflattened[k] = unflatten_dict(v, delimiter)
        else:
            unflattened[k] = v

    d = unflattened
    done = False
    while not done:
        unflattened = {}
        done = True
        for k, v in d.items():
            if delimiter in k:
                done = False
                head, tail = k.rsplit(delimiter, 1)
                if head not in unflattened or not isinstance(unflattened[head], dict):
                    unflattened[head] = {}
                unflattened[head][tail] = v
            else:
                unflattened[k] = v
        d = unflattened
    return d

        
