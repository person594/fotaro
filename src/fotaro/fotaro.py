import os
import sqlite3
import time

from typing import List, Tuple


from .cas import CAS
from .session_manager import SessionManager

import toml

class Fotaro:
    @staticmethod
    def make(data_dir: str) -> None:
        db_file = os.path.join(data_dir, "fotaro.db")
        con = sqlite3.connect(db_file)

        conf_file = os.path.join(data_dir, "fotaro.toml")
        with open(conf_file, 'rb') as f:
            config = toml.load(conf_file)
        
        CAS.make(data_dir, con)

        c = con.cursor()
        c.execute("CREATE TABLE Albums(Hash TEXT NOT NULL, Album TEXT NOT NULL)")
        con.commit()
        
        SessionManager.make(data_dir, con)

    def __init__(self, data_dir):
        db_file = os.path.join(data_dir, "fotaro.db")
        self.con = sqlite3.connect(db_file)
        
        conf_file = os.path.join(data_dir, "fotaro.toml")
        with open(conf_file, 'rb') as f:
            self.config = toml.load(conf_file)


        self.cas = CAS(data_dir, self.con, **self.config.get('CAS', {}))
        self.sm = SessionManager(data_dir, self.con, **self.config.get('SessionManager', {}))


    def get_albums(self) -> List[str]:
        c = self.con.cursor()
        c.execute('SELECT DISTINCT Album FROM Albums')
        return [r[0] for r in c.fetchall()]

    def add_photos_to_album(self, hshes: List[str], album_name: str) -> None:
        c = self.con.cursor()
        for hsh in hshes:
            c.execute("INSERT INTO Albums VALUES (?, ?)", hsh, album_name)
        self.con.commit()

    def remove_photos_from_album(self, hshes: List[str], album_name: str) -> None:
        c = self.con.cursor()
        for hsh in hshes:
            c.execute("DELETE FROM Albums WHERE Hash=? AND Album=?", hsh, album_name)
        self.con.commit()


    # returns: list of (hash, width, height), editable
    def get_list(self, list_name: str) -> Tuple[List[Tuple[str, int, int]], bool]:
        if list_name == "all":
            return self.cas.list_all_photos(), False
        else:
            c = self.con.cursor();
            c.execute("SELECT Photos.Hash, Width, Height FROM Albums INNER JOIN Photos on Albums.Hash=Photos.Hash WHERE Album=? ORDER BY Photos.Timestamp", (album_name))
            result = cast(Iterator[Tuple[str, int, int]], c.fetchall())
            return list(result), True

    def run_daemon(self):
        while True:
            self.cas.update()
            time.sleep(1)
