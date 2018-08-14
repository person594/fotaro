import sys
from photo_store import PhotoStore


def main(db_path: str, watch_dir: str):
    ps = PhotoStore(db_path)
    while True:
        ps.update_dir(watch_dir)

main(sys.argv[1], sys.argv[2])
