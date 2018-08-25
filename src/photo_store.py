import os
import io
import time
from datetime import datetime
import hashlib
import mimetypes
import tarfile
from typing import List, Optional, Any, Tuple, IO, Iterator, overload, cast

from PIL import Image
import sqlite3 as lite

from util import *

def hash_file(path: str) -> str:
    m = hashlib.sha256()
    with open(path, "rb") as f:
        contents = f.read()
    m.update(contents)
    return m.digest().hex()

def image_timestamp(im: Image.Image) -> Optional[int]:
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

def image_mime_type(im: Image.Image) -> str:
    return Image.MIME[im.format]
    

class PhotoStore:
    def __init__(self, data_dir: str) -> None:
        db_file = os.path.join(data_dir, "fotaro.db")
        self.thumbs_dir = os.path.join(data_dir, "thumbs")
        self.thumbnail_height = 350
        self.preferred_extensions = {
            ".jpeg", ".png", ".gif", ".bmp", ".svg"
        }
        self.con = lite.connect(db_file)
        c = self.con.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS Photos(Hash TEXT NOT NULL PRIMARY KEY, Width INT, Height INT, Timestamp INT)")
        c.execute("CREATE TABLE IF NOT EXISTS Files(Path TEXT NOT NULL PRIMARY KEY, Hash TEXT NOT NULL, Modified INT, Mime TEXT NOT NULL)")
        self.con.commit()

    def list_all_photos(self) -> List[Tuple[str, int, int]]:
        c = self.con.cursor()
        c.execute("SELECT Hash, Width, Height FROM Photos WHERE Timestamp IS NOT NULL ORDER BY Timestamp DESC")
        result = cast(Iterator[Tuple[str, int, int]], c.fetchall())
        return list(result)

    # returns: list of (hash, width, height), editable
    def get_list(self, list_name: str) -> Tuple[List[Tuple[str, int, int]], bool]:
        if list_name == "all":
            return self.list_all_photos(), False
        else:
            album_name = escape("Album::" + list_name)
            album_identifier = escape_identifier("Album::" + list_name)
            c = self.con.cursor();
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=%s" % album_name)
            r = c.fetchone()
            if r is not None:
                c.execute("SELECT Photos.Hash, Width, Height FROM %s INNER JOIN Photos ON %s.Hash = Photos.Hash ORDER BY Photos.Timestamp" % (album_identifier, album_identifier))
                result = cast(Iterator[Tuple[str, int, int]], c.fetchall())
                return list(result), True
            else:
                return [], True

    def get_albums(self) -> List[str]:
        c = self.con.cursor();
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Album::%'")
        return [name[len("Album::"):] for (name,) in c.fetchall()]
            
    def add_photos_to_album(self, hashes: List[str], album_name: str) -> None:
        album_identifier = escape_identifier("Album::" + album_name);
        c = self.con.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS %s(Hash TEXT NOT NULL PRIMARY KEY)" % album_identifier)
        for hsh in hashes:
            self._insert(album_identifier, hsh)
        self.con.commit()

    def remove_photos_from_album(self, hashes: List[str], album_name: str) -> None:
        album_identifier = escape_identifier("Album::" + album_name);
        c = self.con.cursor()
        for hsh in hashes:
            c.execute("DELETE FROM %s WHERE Hash=%s" % (album_identifier, escape(hsh)))
        self.con.commit()

    def _insert(self, table: str, *args: Any) -> None:
        c = self.con.cursor()
        args_str = ", ".join([escape(arg) for arg in args])
        c.execute("REPLACE INTO %s VALUES(%s)" % (table, args_str))
        self.con.commit()

    def hash_to_path_mime(self, hsh: str) -> Optional[Tuple[str, str]]:
        c = self.con.cursor()
        c.execute("SELECT Path, Mime from Files WHERE Hash=%s" % escape(hsh))
        r = c.fetchone()
        if r is None:
            return None
        return cast(Tuple[str, str], r)

    def get_photo(self, hsh: str) -> Optional[Tuple[bytes, str]]:
        pm = self.hash_to_path_mime(hsh)
        if pm is None:
            return None
        path, mime = pm
        with open(path, "rb") as f:
            contents = f.read()
        return contents, mime

    def get_photos_tgz(self, hashes: List[str]) -> Tuple[bytes, str]:
        bio =  io.BytesIO()
        with tarfile.open(mode="w:gz", fileobj=bio) as tar:
            for hsh in hashes:
                ext = self.get_photo_extension(hsh)
                pm = self.hash_to_path_mime(hsh)
                if pm is not None:
                    path, _ = pm
                    tar.add(path, arcname=hsh+ext)
        return bio.getvalue(), "application/gzip"
        

    def get_photo_extension(self, hsh: str) -> str:
        pm = self.hash_to_path_mime(hsh)
        if pm is None:
            return ""
        _, mime = pm;
        guessed_extensions = mimetypes.guess_all_extensions(mime);
        for ext in guessed_extensions:
            if ext in self.preferred_extensions:
                return ext
        guessed_extensions.append("");
        return guessed_extensions[0]
        

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
            s = self.thumbnail_height / h
            resized = im.resize((int(w*s), int(h*s)), Image.LANCZOS)
            resized.save(thumb_path, "JPEG")

        with open(thumb_path, "rb") as f:
            contents = f.read()
        return contents, "image/jpeg"


    
    def db_file_last_modified(self, path: str) -> Optional[str]:
        c = self.con.cursor()
        c.execute("SELECT Modified FROM Files WHERE Path=%s" % escape(path))
        r = cast(Optional[Tuple[str]], c.fetchone())
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
            thumb_path = os.path.join(self.thumbs_dir, hsh[:2], hsh[2:] + ".jpg")
            if os.path.isfile(thumb_path):
                os.remove(thumb_path)
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

    
