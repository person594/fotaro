import sqlite3

class Component:
    @staticmethod
    def make(data_dir: str, con: sqlite3.Connection) -> None:
        ...

    def __init__(self, data_dir, **kwargs) -> None:
        self.data_dir = data_dir
        self.db_file = os.path.join(data_dir, "fotaro.db")
        self.con = lite.connect(self.db_file)
