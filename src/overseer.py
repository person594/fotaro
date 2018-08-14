import sys
from photo_store import PhotoStore
import time

def main(db_path: str, watch_dir: str):
    ps = PhotoStore(db_path)
    while True:
        ps.update_dir(watch_dir)
        time.sleep(0.5)

main(sys.argv[1], sys.argv[2])
