import sqlite3

class Component:
    @staticmethod
    def make(data_dir: str, con: sqlite3.Connection) -> None:
        ...

    def __init__(self, fo, **kwargs) -> None:
        ...

    def setup(self):
        ...

    def daemon(self):
        ...

    def __getattr__(self, name):
        if name.startswith('rec_'):
            return []
