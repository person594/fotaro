import sys
from typing import NoReturn

from photo_store import PhotoStore
import time

def run_overseer(data_dir: str, watch_dir: str) -> NoReturn:
    ps = PhotoStore(data_dir)
    while True:
        ps.update_dir(watch_dir)
        time.sleep(0.5)

