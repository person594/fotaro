import os
import io
import time
from datetime import datetime
import hashlib
from typing import List, Optional, Any, Tuple, overload

from PIL import Image
import sqlite3 as lite

def timed(f, *args):
    before = time.time()
    result = f(*args)
    after = time.time()
    print("%s: %.4f seconds" % (f.__name__, after - before))
    return result

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
    if exif is None:
        return None
    if 36867 in exif:
        return int(datetime.strptime(exif[36867], '%Y:%m:%d %H:%M:%S').timestamp())
    else:
        return None

def image_mime_type(im: Image):
    return Image.MIME[im.format]
    

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
    def __init__(self, data_dir: str) -> None:
        db_file = os.path.join(data_dir, "album.db")
        self.thumbs_dir = os.path.join(data_dir, "thumbs")
        self.thumbnail_height = 350
        self.con = lite.connect(db_file)
        c = self.con.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS Photos(Hash TEXT NOT NULL PRIMARY KEY, Width INT, Height INT, Timestamp INT)")
        c.execute("CREATE TABLE IF NOT EXISTS Files(Path TEXT NOT NULL PRIMARY KEY, Hash TEXT NOT NULL, Modified INT, Mime TEXT NOT NULL)")
        self.con.commit()

    def list_all_photos(self):
        c = self.con.cursor()
        c.execute("SELECT Hash, Width, Height FROM Photos WHERE Timestamp IS NOT NULL ORDER BY Timestamp DESC")
        return list(c.fetchall())

    def get_list(self, list_name):
        if list_name == "all":
            return self.list_all_photos()
        else:
            return []

    def _insert(self, table: str, *args: Any):
        c = self.con.cursor()
        args_str = ", ".join([escape(arg) for arg in args])
        c.execute("REPLACE INTO %s VALUES(%s)" % (table, args_str))
        self.con.commit()

    def hash_to_path_mime(self, hsh: str) -> Optional[str]:
        c = self.con.cursor()
        c.execute("SELECT Path, Mime from Files WHERE Hash=%s" % escape(hsh))
        r = c.fetchone()
        if r is None:
            return None
        return r

    def get_photo(self, hsh: str) -> Optional[Tuple[bytes, str]]:
        pm = self.hash_to_path_mime(hsh)
        if pm is None:
            return None
        path, mime = pm
        with open(path, "rb") as f:
            contents = f.read()
        return contents, mime

    def get_thumbnail(self, hsh: str) -> Optional[Tuple[bytes, str]]:
        thumb_dir = os.path.join(self.thumbs_dir, hsh[:2])
        if not os.path.isdir(thumb_dir):
            os.makedirs(thumb_dir)
        thumb_path = os.path.join(thumb_dir, hsh[2:] + ".jpg")

        if not os.path.isfile(thumb_path):
            pm = self.hash_to_path_mime(hsh)
            if pm is None:
                return None
            path, _ = pm
            im = Image.open(path)
            w, h = im.size
            f = self.thumbnail_height / h
            resized = timed(im.resize, (int(w*f), int(h*f)), Image.ANTIALIAS)
            resized.save(thumb_path, "JPEG")

        with open(thumb_path, "rb") as f:
            contents = f.read()
        return contents, "image/jpeg"


    
    def db_file_last_modified(self, path: str) -> Optional[str]:
        c = self.con.cursor()
        c.execute("SELECT Modified FROM Files WHERE Path=%s" % escape(path))
        r = c.fetchone()
        if r is not None:
            return r[0]
        else:
            return None
        
    def add_file(self, path: str) -> None:
        try:
            modified = int(os.path.getmtime(path))
            if modified == self.db_file_last_modified(path):
                return
            im = Image.open(path)
            w, h = im.size
            timestamp = image_timestamp(im)
            mime = image_mime_type(im)
            hsh = hash_file(path)
            self.remove_file(path)
            print("Adding file %s" % path)
            self._insert("Photos", hsh, w, h, timestamp)
            self._insert("Files", path, hsh, modified, mime)
            self.get_thumbnail(hsh)
        except OSError:
            pass

    def remove_file(self, path: str) -> None:
        c = self.con.cursor()
        c.execute("SELECT Hash FROM Files WHERE Path=%s" % escape(path))
        hsh = c.fetchone()
        if hsh is None:
            # path was not in the db
            return
        hsh = hsh[0]
        print("Removing file %s" % path)
        c.execute("DELETE FROM Files WHERE Path=%s" % escape(path))
        # if that was the only copy of the photo, remove it from the photos table
        c.execute("SELECT * FROM Files WHERE HASH=%s" % escape(hsh))
        if c.fetchone() is None:
            print("Removing photo %s" % hsh)
            c.execute("DELETE FROM Photos WHERE HASH=%s" % escape(hsh))
            thumb_path = os.path.join(self.thumbs_path, hsh[:2], hsh[2:] + ".jpg")
            if os.path.isfile(thumb_path):
                #os.remove(thumb_path)
                print(thumb_path)
        self.con.commit()
            
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

    
