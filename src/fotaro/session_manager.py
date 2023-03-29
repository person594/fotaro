import sqlite3
import hashlib
import pickle
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import os
from http.cookies import SimpleCookie
from email.utils import format_datetime

from flask import request, make_response, jsonify

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
    def make(data_dir: str, con: "ManagedDBConnection") -> None:
        import getpass

        with con() as c:
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
        with con() as c:
            c.execute("INSERT INTO Users VALUES(?, ?, ?)", (username, salt.hex(), passhash.hex()))
    
    def __init__(self, fo) -> None:
        self.fo = fo
        self.max_sessions_per_user = 64
        self.short_term_session_timeout = timedelta(days=1)
        self.long_term_session_timeout = timedelta(days=365)

    def get_username(self, sess_id=None):
        if sess_id is None:
            sess_id = request.cookies.get('sess_id')
        if sess_id is None:
            return None
        return self.session_user(sess_id)

        
    def setup(self):
        @self.fo.server.route("/login", methods=['POST'])
        def serve_login():
            try:
                username = request.json['username']
                password = request.json['password']
            except KeyError:
                abort(400)
            sess_id_expires = self.login(username, password)
            if sess_id_expires is not None:
                sess_id, expires = sess_id_expires
                resp = make_response(username)
                resp.set_cookie('sess_id', sess_id, expires=expires)
                return resp
            else:
                return "Invalid username or password", 401

        @self.fo.server.route("/username")
        def serve_username():
            sess_id = request.cookies.get('sess_id')
            if sess_id is None:
                return jsonify(None)
            return jsonify(self.session_user(sess_id))

        @self.fo.server.route("/logout")
        def serve_logout():
            sess_id = request.cookies.get('sess_id')
            if sess_id is not None:
                self.end_session(sess_id)
            return jsonify(None)

        @self.fo.server.route("/passwordChange", methods=["POST"])
        def serve_password_change():
            try:
                old_password = request.json['oldPassword']
                new_password = request.json['newPassword']
            except KeyError:
                abort(400)
            username = self.get_username()
            if username is None:
                abort(400)
            if self.authenticate(username, old_password):
                self.set_password(username, new_password)
                return "", 200
            else:
                return "Invalid password", 401            

    # call this before we read from the sessions table
    def garbage_collect_sessions(self) -> None:
        now = now_timestamp()
        with self.fo.con() as c:
            c.execute("DELETE FROM Sessions WHERE Expires<?", (now,))
        
    def make_user(self, username: str, password: str) -> None:
        with self.fo.con(True) as c:
            c.execute("SELECT * FROM Users WHERE Username=%s", (username,))
            if c.fetchone() is not None:
                raise UserAlreadyExistsException(username)
        salt = os.urandom(32)
        m = hashlib.sha256()
        m.update(bytes(password, encoding="utf-8") + salt)
        passhash = m.digest()
        with self.fo.con() as c:
            c.execute("INSERT INTO Users VALUES(?, ?, ?)", (username, salt.hex(), passhash.hex()))

    def set_password(self, username: str, password: str) -> None:
        with self.fo.con(True) as c:
            c.execute("SELECT * FROM Users WHERE Username=?", (username,))
            if c.fetchone() is None:
                raise NoSuchUserException(username)
        salt = os.urandom(32)
        m = hashlib.sha256()
        m.update(bytes(password, encoding="utf-8") + salt)
        passhash = m.digest()
        with self.fo.con() as c:
            c.execute("UPDATE Users SET Salt=?, Passhash=? WHERE Username=?", (salt.hex(), passhash.hex(), username))

    def make_session(self, username: str) -> Optional[Tuple[str, datetime]]:
        self.garbage_collect_sessions()
        with self.fo.con(True) as c:
            c.execute("SELECT SessionID FROM Sessions WHERE Username=?", (username,))
            if len(list(c.fetchall())) > self.max_sessions_per_user:
                return None
        sess_id = os.urandom(32).hex()

        expires = datetime.now(timezone.utc) + self.short_term_session_timeout

        with self.fo.con() as c:
            c.execute("INSERT INTO Sessions VALUES(?, ?, ?)", (sess_id, username, utc_to_timestamp(expires)))
        return sess_id, expires

    def session_user(self, sess_id: str) -> Optional[str]:
        self.garbage_collect_sessions()
        with self.fo.con(True) as c:
            c.execute("SELECT Username FROM Sessions WHERE SessionID=?", (sess_id,))
            r = c.fetchone()
        if r is None:
            return None
        assert isinstance(r[0], str)
        return r[0]

    def end_session(self, sess_id: str) -> None:
        with self.fo.con() as c:
            c.execute("DELETE FROM Sessions WHERE SessionID=?", (sess_id,))

    def authenticate(self, username: str, password: str) -> bool:
        with self.fo.con(True) as c:
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

    def login(self, username: str, password: str) -> Optional[Tuple[str, datetime]]:
        if self.authenticate(username, password):
            return self.make_session(username)
        else:
            return None
