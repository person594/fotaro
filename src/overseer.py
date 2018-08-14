import sys
from photo_store import PhotoStore


def main(watch_dir: str, db_path: str):
    ps = PhotoStore(db_path)
    while True:
        ps.update_dir(watch_dir)
