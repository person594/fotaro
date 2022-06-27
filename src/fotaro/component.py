import sqlite3

class Component:
    @staticmethod
    def make(data_dir: str, con: sqlite3.Connection) -> None:
        ...

    def __init__(self, data_dir, **kwargs) -> None:
        ...


    def get_sort_bys(self):
        return []

    def get_search_filters(self):
        return []
