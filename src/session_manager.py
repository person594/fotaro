import sqlite3 as lite
import hashlib
import pickle
from datetime import datetime, timedelta, timezone
from typing import Optional
import os
from http.cookies import SimpleCookie
from email.utils import format_datetime

from util import *

class UserAlreadyExistsException(Exception):
    def __init__(self, username: str) -> None:
        super().__init__("A user with the name %s already exists" % username)

class SessionManager:
    def __init__(self, data_dir: str) -> None:
        db_file = os.path.join(data_dir, "fotaro.db")
        self.con = lite.connect(db_file)
        self.max_sessions_per_user = 64
        self.short_term_session_timeout = timedelta(days=1)
        self.long_term_session_timeout = timedelta(days=365)
        c = self.con.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS Users(Username TEXT NOT NULL PRIMARY KEY, Salt TEXT NOT NULL, Passhash TEXT NOT NULL)")
        c.execute("CREATE TABLE IF NOT EXISTS Sessions(SessionID TEXT NOT NULL PRIMARY KEY, Username TEXT NOT NULL, Expires INTEGER NOT NULL)")
        
    def make_user(self, username: str, password: str) -> None:
        c = self.con.cursor()
        c.execute("SELECT * FROM Users WHERE Username=%s" % escape(username))
        if c.fetchone() is not None:
            raise UserAlreadyExistsException(username)
        salt = os.urandom(32)
        m = hashlib.sha256()
        m.update(bytes(password, encoding="utf-8") + salt)
        passhash = m.digest()
        c.execute("INSERT INTO Users VALUES(%s, %s, %s)" % (escape(username), escape(salt.hex()), escape(passhash.hex())))
        self.con.commit()
        
    def make_session(self, username: str, long_term: bool = False) -> Optional[SimpleCookie]:
        c = self.con.cursor()
        c.execute("SELECT SessionID FROM Sessions WHERE Username=%s" % escape(username))
        if len(list(c.fetchall())) > self.max_sessions_per_user:
            return None
        sess_id = os.urandom(32).hex()
        if long_term:
            expires = datetime.now(timezone.utc) + self.long_term_session_timeout
        else:
            expires = datetime.now(timezone.utc) + self.short_term_session_timeout

        cookie = SimpleCookie()
        cookie["sess_id"] = sess_id
        if long_term:
            cookie["sess_id"]["expires"] = format_datetime(expires, True)
        c.execute("INSERT INTO Sessions VALUES(%s, %s, %s)" % (escape(sess_id), escape(username), escape(utc_to_timestamp(expires))))
        self.con.commit()
        return cookie
        
        
    def authenticate(self, username: str, password: str) -> Optional[SimpleCookie]:
        c = self.con.cursor()
        c.execute("SELECT * FROM Users WHERE Username=%s" % escape(username))
        r = c.fetchone()
        if r is None:
            return None
        username, salt, passhash = r
        # no password set
        if salt is None or passhash is None:
            return None
        m = hashlib.sha256()
        m.update(bytes(password, encoding="utf-8") + bytes.fromhex(salt))
        if m.digest() == bytes.fromhex(passhash):
            return self.make_session(username)
        else:
            return None
