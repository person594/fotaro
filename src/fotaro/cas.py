from __future__ import annotations

import os
import io
import json
import time
from datetime import datetime
import hashlib
import mimetypes
import tarfile
from dataclasses import dataclass
from typing import List, Optional, Any, Tuple, IO, Iterator, overload, cast

from PIL import Image
import sqlite3

from .component import Component
from .util import *

def _hash_file(path: str) -> str:
    m = hashlib.sha256()
    with open(path, "rb") as f:
        contents = f.read()
    m.update(contents)
    return m.digest().hex()

def _image_timestamp(im: Image.Image) -> Optional[int]:
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

def _image_mime_type(im: Image.Image) -> str:
    return Image.MIME[im.format]

# we need this since exif orientation can flip w and h
def _image_shape(im: Image.Image) -> Tuple[int, int]:
    rw, rh = im.size
    try:
        exif = im._getexif()
    except AttributeError:
        return rw, rh
    if exif is None:
        return rw, rh
    orientation = exif.get(274, 1)
    if orientation > 4:
        return rh, rw
    return rw, rh        

class CAS(Component):

    @dataclass
    class Photo:
        hsh: str
        path: str
        mime: str
        thumb_path: str
        thumb_mime: str
        width: int
        height: int
        timestamp: int

        def pil(self):
            with Image.open(self.path) as img:
                img.load()
            return img

        def thumb_pil(self):
            with Image.open(self.thumb_path) as img:
                img.load()
            return img


    @staticmethod
    def make(data_dir: str, con: "ManagedDBConnection") -> None:
        thumbs_dir = os.path.join(data_dir, "thumbs")
        os.mkdir(thumbs_dir)
        with con() as c:
            c.execute("CREATE TABLE Photos(Hash TEXT NOT NULL PRIMARY KEY, Width INT, Height INT, Timestamp INT)")
            c.execute("CREATE TABLE Files(Path TEXT NOT NULL PRIMARY KEY, Hash TEXT NOT NULL, Modified INT, Mime TEXT NOT NULL)")
       
    def __init__(self, fo,
                 content_dirs: List[str],
                 thumb_height: str = 350,
                 preferred_extensions: List[str] = [".jpeg", ".png", ".gif", ".bmp", ".svg"]
                 ) -> None:
        self.fo = fo

        self.thumbs_dir = os.path.join(fo.data_dir, "thumbs")
        self.content_dirs = content_dirs
        self.thumb_height = thumb_height
        
        self.preferred_extensions = set(preferred_extensions)

    def __iter__(self):
        with self.fo.con(True) as c:
            c.execute("SELECT Photos.Hash, min(Path), Mime, Width, Height, Timestamp FROM Photos INNER JOIN Files ON Photos.Hash=Files.HASH GROUP BY Photos.Hash ORDER BY Timestamp DESC")
            results = c.fetchall()
        for hsh, path, mime, width, height, timestamp in results:
            thumb_path, thumb_mime = self.thumb_path_mime(hsh)
            yield CAS.Photo(hsh, path, mime, thumb_path, thumb_mime, width, height, timestamp)


    def __getitem__(self, hsh):
        if not isinstance(hsh, str):
            raise TypeError("Hashes must be strings")
        with self.fo.con() as c:
            c.execute("SELECT Photos.Hash, Path, Mime, Width, Height, Timestamp FROM Photos INNER JOIN Files ON Photos.Hash=Files.HASH WHERE Photos.Hash = ? ORDER BY Path ASC", (hsh,))
            r = c.fetchone()
        if r is None:
            raise IndexError("Hash not in CAS")
        else:
            hsh, path, mime, width, height, timestamp = r
            thumb_path, thumb_mime = self.thumb_path_mime(hsh)
            return CAS.Photo(hsh, path, mime, thumb_path, thumb_mime, width, height, timestamp)
        
        
    def list_all_photos(self) -> List[Tuple[str, int, int]]:
        with self.fo.con(True) as c:
            c.execute("SELECT Hash, Width, Height FROM Photos ORDER BY Timestamp DESC")
            result = cast(Iterator[Tuple[str, int, int]], c.fetchall())
        return list(result)


    """
    def get_albums(self) -> List[str]:
        c = self.fo.con.cursor();
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Album::%'")
        return [name[len("Album::"):] for (name,) in c.fetchall()]
            
    def add_photos_to_album(self, hashes: List[str], album_name: str) -> None:
        album_identifier = escape_identifier("Album::" + album_name);
        c = self.fo.con.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS %s(Hash TEXT NOT NULL PRIMARY KEY)" % album_identifier)
        for hsh in hashes:
            self._insert(album_identifier, hsh)
        self.fo.con.commit()

    def remove_photos_from_album(self, hashes: List[str], album_name: str) -> None:
        album_identifier = escape_identifier("Album::" + album_name);
        c = self.fo.con.cursor()
        for hsh in hashes:
            c.execute("DELETE FROM %s WHERE Hash=%s" % (album_identifier, escape(hsh)))
        self.fo.con.commit()
    """
    
    def hash_to_path_mime(self, hsh: str) -> Optional[Tuple[str, str]]:
        with self.fo.con(True) as c:
            c.execute("SELECT Path, Mime from Files WHERE Hash=?", (hsh,))
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


    def _make_thumb(self, hsh: str, path: str) -> None:
        thumb_dir = os.path.join(self.thumbs_dir, hsh[:2])
        if not os.path.isdir(thumb_dir):
            os.makedirs(thumb_dir)
        thumb_path = os.path.join(thumb_dir, hsh[2:] + ".jpeg")
        if not os.path.isfile(thumb_path):
            im = Image.open(path)
            # TODO: detect if image is exif-rotated
            exif = bytes(im.info.get('exif', b''))
            w, h = im.size
            s = self.thumb_height / h
            resized = im.resize((int(w*s), int(h*s)), Image.LANCZOS)
            resized.save(thumb_path, "JPEG", exif=exif)

    def thumb_path_mime(self, hsh: str) -> Tuple[str, str]:
        thumb_dir = os.path.join(self.thumbs_dir, hsh[:2])
        thumb_path = os.path.join(thumb_dir, hsh[2:] + ".jpeg")
        return thumb_path, "image/jpeg"

    def get_thumb(self, hsh: str) -> Optional[Tuple[bytes, str]]:
        thumb_dir = os.path.join(self.thumbs_dir, hsh[:2])
        if not os.path.isdir(thumb_dir):
            os.makedirs(thumb_dir)
        thumb_path = os.path.join(thumb_dir, hsh[2:] + ".jpeg")

        if not os.path.isfile(thumb_path):
            pm = self.hash_to_path_mime(hsh)
            if pm is None:
                return None
            path, _ = pm
            im = Image.open(path)
            exif = bytes(im.info.get('exif', b''))
            w, h = im.size
            s = self.thumb_height / h
            resized = im.resize((int(w*s), int(h*s)), Image.LANCZOS)
            resized.save(thumb_path, "JPEG", exif=exif)

        with open(thumb_path, "rb") as f:
            contents = f.read()
        return contents, "image/jpeg"


    
    def db_file_last_modified(self, path: str) -> Optional[str]:
        with self.fo.con(True) as c:
            c.execute("SELECT Modified FROM Files WHERE Path=?", (path,))
            r = cast(Optional[Tuple[str]], c.fetchone())
        if r is not None:
            return r[0]
        else:
            return None
        
    def _add_file(self, path: str) -> None:
        try:
            modified = int(os.path.getmtime(path))
            im = Image.open(path)
            w, h = _image_shape(im)
            timestamp = _image_timestamp(im)
            mime = _image_mime_type(im)
            hsh = _hash_file(path)
            self._remove_file(path)
            print("Adding file %s" % path)
            self._make_thumb(hsh, path)
            with self.fo.con() as c:
                c.execute("REPLACE INTO Photos VALUES(?, ?, ?, ?)", (hsh, w, h, timestamp))
                c.execute("REPLACE INTO Files VALUES(?, ?, ?, ?)", (path, hsh, modified, mime))
        except OSError:
            pass

    def _remove_file(self, path: str) -> None:
        with self.fo.con() as c:
            c.execute("SELECT Hash FROM Files WHERE Path=?", (path,))
            hsh = c.fetchone()
            if hsh is None:
                # path was not in the db
                return
            hsh = hsh[0]
            print("Removing file %s" % path)
            c.execute("DELETE FROM Files WHERE Path=?", (path,))
            # if that was the only copy of the photo, remove it from the photos table
            c.execute("SELECT * FROM Files WHERE HASH=?", (hsh,))
            if c.fetchone() is None:
                print("Removing photo %s" % hsh)
                c.execute("DELETE FROM Photos WHERE HASH=?", (hsh,))
                delete_thumb = True
            else:
                delete_thumb = False
        if delete_thumb:
            thumb_path = os.path.join(self.thumbs_dir, hsh[:2], hsh[2:] + ".jpeg")
            if os.path.isfile(thumb_path):
                os.remove(thumb_path)

    def daemon(self):
        while True:
            self.update()
            time.sleep(0.1)
                
    def update(self) -> None:
        # get all the paths in the fs
        fs_paths_modified = {}
        for path in self.content_dirs:
            for dirpath, _, fnames in os.walk(path):
                for fname in fnames:
                    fs_path = os.path.join(dirpath, fname)
                    fs_modified = int(os.path.getmtime(fs_path))
                    fs_paths_modified[fs_path] = fs_modified
            # query all the paths in the db, along with the modified te
            with self.fo.con(True) as c:
                c.execute("SELECT Path, Modified FROM Files WHERE Path LIKE ?", (path + "%",))
                res = c.fetchall()
            db_paths_modified = {}
            for db_path, db_modified in res:
                db_paths_modified[db_path] = db_modified
            # add new files
            for fs_path, fs_modified in fs_paths_modified.items():
                if fs_path not in db_paths_modified:
                    self._add_file(fs_path)
                elif fs_modified > db_paths_modified[fs_path]:
                    self._add_file(fs_path)
            # remove old files
            for db_path in db_paths_modified:
                if db_path not in fs_paths_modified:
                    self._remove_file(db_path)

