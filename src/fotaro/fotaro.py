import os
import sqlite3
import time
from importlib import import_module
import threading

from typing import List, Tuple, Optional

from .server import Server
from .cas import CAS
from .session_manager import SessionManager
from .search import Search
from .formulaic import formulaic

import toml


class ManagedDBConnection:
    class CM:
        def __init__(self, mcon, readonly=False):
            self.mcon = mcon
            self.readonly = readonly

        def __enter__(self):
            if self.readonly:
                self.cursor = self.mcon._con_ro.cursor()
                
            else:
                self.mcon._lock.acquire()
                self.cursor = self.mcon._con.cursor()
            return self.cursor
        
        def __exit__(self, exc_type, exc_value, traceback):
            self.cursor.close()
            if not self.readonly:
                self.mcon._con.commit()
                self.mcon._lock.release()

    def __init__(self, db_file):
        self.db_file = db_file
        self._tl = threading.local()
        self._lock = threading.Lock()

    def _connect(self, readonly=False):
        uri = "file:" + self.db_file
        if readonly:
            uri += "?mode=ro"
        return sqlite3.connect(uri, uri=True, detect_types=sqlite3.PARSE_DECLTYPES)
        
    @property
    def _con(self):
        if not hasattr(self._tl, 'con'):
            self._tl.con = self._connect(False)
        return self._tl.con

    @property
    def _con_ro(self):
        if not hasattr(self._tl, 'con_ro'):
            self._tl.con_ro = self._connect(True)
        return self._tl.con_ro

    
    def __call__(self, readonly=False):
        return ManagedDBConnection.CM(self, readonly)

    def __enter__(self):
        return self().__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        return self().__exit__(exc_type, exc_value, traceback)

            
class Fotaro:
    @staticmethod
    def make(data_dir: str) -> None:
        db_file = os.path.join(data_dir, "fotaro.db")
        con = ManagedDBConnection(db_file)

        conf_file = os.path.join(data_dir, "fotaro.toml")
        with open(conf_file, 'rb') as f:
            config = toml.load(conf_file)
        
        CAS.make(data_dir, con)

        with con() as c:
            c.execute("CREATE TABLE Albums(Hash TEXT NOT NULL, Album TEXT NOT NULL)")
        
        SessionManager.make(data_dir, con)

        Search.make(data_dir, con)

        Server.make(data_dir, con)

        plugins= config.get('plugin', {})
        for plugin_name, plugin_config in plugins.items():
            module_name, class_name = plugin_config['class'].rsplit('.', 1)
            module = import_module(module_name)
            plugin_class = getattr(module, class_name)
            plugin_class.make(data_dir, con)
            

    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.db_file = os.path.join(data_dir, "fotaro.db")
        self.con = ManagedDBConnection(self.db_file)
        self._tl = threading.local()
        
        conf_file = os.path.join(data_dir, "fotaro.toml")
        with open(conf_file, 'rb') as f:
            self.config = toml.load(conf_file)


        self.cas = CAS(self, **self.config.get('CAS', {}))
        self.sm = SessionManager(self, **self.config.get('SessionManager', {}))
        self.search = Search(self, **self.config.get('Search', {}))
        self.server = Server(self, **self.config.get('Server', {}))

        self.plugins = {}
        
        plugins = self.config.get('plugin', {})
        for plugin_name, plugin_config in plugins.items():
            module_name, class_name = plugin_config['class'].rsplit('.', 1)
            module = import_module(module_name)
            plugin_class = getattr(module, class_name)
            plugin_config = dict(plugin_config)
            del plugin_config['class']
            self.plugins[plugin_name] = plugin_class(self, **plugin_config)

        self.components = [self.cas, self.sm, self.search, self.server] + list(self.plugins.values())

    def __getattr__(self, name):
        if name.startswith('rec_'):
            resources = []
            for component in self.components:
                resources.extend(getattr(component, name))
            return resources
        
    def get_albums(self) -> List[str]:
        with self.con(True) as c:
            c.execute('SELECT DISTINCT Album FROM Albums')
            return [r[0] for r in c.fetchall()]

    def add_photos_to_album(self, hshes: List[str], album_name: str) -> None:
        with self.con() as c:
            for hsh in hshes:
                c.execute("INSERT INTO Albums VALUES (?, ?)", (hsh, album_name))

    def remove_photos_from_album(self, hshes: List[str], album_name: str) -> None:
        with self.con() as c:
            for hsh in hshes:
                c.execute("DELETE FROM Albums WHERE Hash=? AND Album=?", (hsh, album_name))


    # returns: list of (hash, width, height), editable
    def get_list(self, list_name: str) -> Tuple[List[Tuple[str, int, int]], bool]:
        if list_name == "all":
            return self.cas.list_all_photos(), False
        else:
            with self.con(True) as c:
                c.execute("SELECT Photos.Hash, Width, Height FROM Albums INNER JOIN Photos on Albums.Hash=Photos.Hash WHERE Album=? ORDER BY Photos.Timestamp", (list_name,))
                return c.fetchall(), True

    def run(self):
        for component in self.components:
            component.setup()

        for component in self.components:
            daemon_thread = threading.Thread(target=component.daemon)
            daemon_thread.start()
