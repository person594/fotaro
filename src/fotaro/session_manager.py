import sqlite3
import hashlib
import pickle
from datetime import datetime, timedelta, timezone
from typing import Optional
import os
from http.cookies import SimpleCookie
from email.utils import format_datetime

from .component import Component

from .util import *

class UserAlreadyExistsException(Exception):
    def __init__(self, username: str) -> None:
        super().__init__("A user with the name %s already exists" % username)

class NoSuchUserException(Exception):
    def __init__(self, username: str) -> None:
        super().__init__("No user with the name %s" % username)

class SessionManager(Component):

    @staticmethod
    def make(data_dir: str, con: sqlite3.Connection) -> None:
        import getpass
        
        c = con.cursor()
        c.execute("CREATE TABLE Users(Username TEXT NOT NULL PRIMARY KEY, Salt TEXT NOT NULL, Passhash TEXT NOT NULL)")
        c.execute("CREATE TABLE Sessions(SessionID TEXT NOT NULL PRIMARY KEY, Username TEXT NOT NULL, Expires INTEGER NOT NULL)")

        # make default user
        username = input("Enter default username: ")
        while True:
            password = getpass.getpass("Password for user %s: " % username)
            confirm = getpass.getpass("Confirm password for user %s: " % username)
            if password == confirm:
                break
            print("Oops, passwords mismatched")
    
        salt = os.urandom(32)
        m = hashlib.sha256()
        m.update(bytes(password, encoding="utf-8") + salt)
        passhash = m.digest()
        c.execute("INSERT INTO Users VALUES(?, ?, ?)", (username, salt.hex(), passhash.hex()))
        con.commit()
    
    def __init__(self, data_dir: str, con: sqlite3.Connection) -> None:
        self.con = con
        self.max_sessions_per_user = 64
        self.short_term_session_timeout = timedelta(days=1)
        self.long_term_session_timeout = timedelta(days=365)
        c = self.con.cursor()

        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Users'")
        if c.fetchone() is None:
            # if the table doesn't exist, initialize it with a root
            c.execute("CREATE TABLE Users(Username TEXT NOT NULL PRIMARY KEY, Salt TEXT NOT NULL, Passhash TEXT NOT NULL)")
            c.execute("CREATE TABLE Sessions(SessionID TEXT NOT NULL PRIMARY KEY, Username TEXT NOT NULL, Expires INTEGER NOT NULL)")
            self.con.commit()
            self.make_user('root', 'root')

    # call this before we read from the sessions table
    def garbage_collect_sessions(self) -> None:
        c = self.con.cursor()
        now = now_timestamp()
        c.execute("DELETE FROM Sessions WHERE Expires<?", (now,))
        self.con.commit()
        
    def make_user(self, username: str, password: str) -> None:
        c = self.con.cursor()
        c.execute("SELECT * FROM Users WHERE Username=%s", (username,))
        if c.fetchone() is not None:
            raise UserAlreadyExistsException(username)
        salt = os.urandom(32)
        m = hashlib.sha256()
        m.update(bytes(password, encoding="utf-8") + salt)
        passhash = m.digest()
        c.execute("INSERT INTO Users VALUES(?, ?, ?)", (username, salt.hex(), passhash.hex()))
        self.con.commit()

    def set_password(self, username: str, password: str) -> None:
       c = self.con.cursor()
       c.execute("SELECT * FROM Users WHERE Username=?", (username,))
       if c.fetchone() is None:
           raise NoSuchUserException(username)
       salt = os.urandom(32)
       m = hashlib.sha256()
       m.update(bytes(password, encoding="utf-8") + salt)
       passhash = m.digest()
       c.execute("UPDATE Users SET Salt=?, Passhash=? WHERE Username=?", (salt.hex(), passhash.hex(), username))
       self.con.commit()
        
    def make_session(self, username: str, long_term: bool = False) -> Optional[SimpleCookie]:
        self.garbage_collect_sessions()
        c = self.con.cursor()
        c.execute("SELECT SessionID FROM Sessions WHERE Username=?", (username,))
        if len(list(c.fetchall())) > self.max_sessions_per_user:
            return None
        sess_id = os.urandom(32).hex()
        if long_term:
            expires = datetime.now(timezone.utc) + self.long_term_session_timeout
        else:
            expires = datetime.now(timezone.utc) + self.short_term_session_timeout

        cookie = SimpleCookie()
        cookie["test_field"] = "lol"
        cookie["sess_id"] = sess_id
        if long_term:
            cookie["sess_id"]["expires"] = format_datetime(expires, True)
        c.execute("INSERT INTO Sessions VALUES(?, ?, ?)", (sess_id, username, utc_to_timestamp(expires)))
        self.con.commit()
        return cookie

    def session_user(self, sess_id: str) -> Optional[str]:
        self.garbage_collect_sessions()
        c = self.con.cursor()
        c.execute("SELECT Username FROM Sessions WHERE SessionID=?", (sess_id,))
        r = c.fetchone()
        if r is None:
            return None
        assert isinstance(r[0], str)
        return r[0]

    def end_session(self, sess_id: str) -> None:
        c = self.con.cursor()
        c.execute("DELETE FROM Sessions WHERE SessionID=?", (sess_id,))
        self.con.commit()

    def authenticate(self, username: str, password: str) -> bool:
        c = self.con.cursor()
        c.execute("SELECT * FROM Users WHERE Username=?", (username,))
        r = c.fetchone()
        if r is None:
            # user not found
            return False
        username, salt, passhash = r
        # no password set
        if salt is None or passhash is None:
            return False
        m = hashlib.sha256()
        m.update(bytes(password, encoding="utf-8") + bytes.fromhex(salt))
        if m.digest() == bytes.fromhex(passhash):
            return True
        else:
            # bad password
            return False

    def login(self, username: str, password: str) -> Optional[SimpleCookie]:
        if self.authenticate(username, password):
            return self.make_session(username)
        else:
            return None
