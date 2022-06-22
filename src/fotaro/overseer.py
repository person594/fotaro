import sys
from typing import NoReturn

from cas import CAS
import time

def run_overseer(data_dir: str) -> NoReturn:
    cas = CAS(data_dir)
    while True:
        cas.update_dir()
        time.sleep(0.5)

