import os
from datetime import datetime
import hashlib
from typing import List, Optional, Any, overload

from PIL import Image
import sqlite3 as lite

def hash_file(path: str) -> str:
    m = hashlib.sha256()
    with open(path, "rb") as f:
        contents = f.read()
    m.update(contents)
    return m.digest().hex()

def image_timestamp(im: Image) -> Optional[int]:
    try:
        exif = im._getexif()
    except AttributeError:
        return None
    if 36867 in exif:
        return int(datetime.strptime(exif[36867], '%Y:%m:%d %H:%M:%S').timestamp())
    else:
        return None

def escape(x: Any) -> str:
    if x is None:
        return "NULL"
    elif isinstance(x, str):
        return "'" + str_escape(x) + "'"
    elif isinstance(x, int):
        return str(x)
    else:
        return escape(repr(x))

def str_escape(s: str) -> str:
    return s.replace("'", "''")
    
class PhotoStore:
    def __init__(self, db_file: str) -> None:
        self.db_file = db_file
        self.con = lite.connect(db_file)
        c = self.con.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS Photos(Hash TEXT NOT NULL PRIMARY KEY, Width INT, Height INT, Timestamp INT)")
        c.execute("CREATE TABLE IF NOT EXISTS Files(Path TEXT NOT NULL PRIMARY KEY, Hash TEXT NOT NULL)")
        self.con.commit()

    def _insert(self, table: str, *args: Any):
        c = self.con.cursor()
        args_str = ", ".join([escape(arg) for arg in args])
        c.execute("REPLACE INTO %s VALUES(%s)" % (table, args_str))
        self.con.commit()

    def file_hash(self, path: str) -> Optional[str]:
        c = self.con.cursor()
        c.execute("SELECT Hash FROM Files WHERE Path=%s" % escape(path))
        r = c.fetchone()
        if r is not None:
            return r[0]
        else:
            return None
        
    def add_file(self, path: str) -> None:
        try:
            hsh = hash_file(path)
            if hsh == self.file_hash(path):
                return
            im = Image.open(path)
            w, h = im.size
            timestamp = image_timestamp(im)
            self.remove_file(path)
            self._insert("Photos", hsh, w, h, timestamp)
            self._insert("Files", path, hsh)
        except OSError:
            pass

    def remove_file(self, path: str) -> None:
        c = self.con.cursor()
        c.execute("SELECT Hash FROM Files WHERE Path=%s" % escape(path))
        hsh = c.fetchone()
        if hsh is None:
            # path was not in the db
            return
        c.execute("DELETE FROM Files WHERE Path=%s" % escape(path))
        # if that was the only copy of the photo, remove it from the photos table
        c.execute("SELECT * FROM Photos WHERE HASH=%s" % escape(hsh))
        if c.fetchone() is None:
            c.execute("DELETE FROM Photos WHERE HASH=%s" % escape(hsh))

    def update_dir(self, path: str) -> None:
        paths = set()
        for dirpath, _, fnames in os.walk(path):
            for fname in fnames:
                paths.add(os.path.join(dirpath, fname))
        # query the files we think are in that directory, and remove the ones that don't exist anymore
        c = self.con.cursor()
        c.execute("SELECT Path FROM Files WHERE Path LIKE '%s%%'" % str_escape(path))
        for (path,) in c.fetchall():
            if path not in paths:
                self.remove_file(path)
        # update the files that d
        for path in paths:
            self.add_file(path)

    
