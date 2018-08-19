import sys
from typing import List, Any, Dict

def docopt(
    doc: str,
    argv:List[str] = sys.argv[1:],
    help: bool = True,
    version: Any = None,
    options_first: bool = False
) -> Dict[str, str]:
    ...
