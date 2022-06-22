import sys
import os
import json
import mimetypes
import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from http.cookies import BaseCookie
from typing import Optional, Dict, Any


from cas import CAS
from session_manager import SessionManager

def run_server(data_dir: str) -> None:
    cas = CAS(data_dir)
    sm = SessionManager(data_dir)
    class RequestHandler(BaseHTTPRequestHandler):
        def send_cookie(self, c: BaseCookie) -> None:
            for key in c:
                self.send_header('Set-Cookie', c[key].output(header=''))
                
            
        def serve_static(self, path: str) -> None:
            path = os.path.normpath(path)[1:]
            if path == "":
                path = "photos.html"
            if "." not in path:
                path = path + ".html"
            path = os.path.join("../../static/", path)
            print(path)
            if os.path.isfile(path):
                with open(path, "rb") as f:
                    contents = f.read()
                self.send_response(200)
                mime, _ = mimetypes.guess_type(path)
                if mime is None:
                    mime = "application/octet-stream"
                self.send_header('Content-type', mime)
                self.end_headers()
                self.wfile.write(contents)
            else:
                self.serve_404()

        def serve_text(self, text: str, status: int = 200) -> None:
            self.send_response(status)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(bytes(text, "utf8"))

        def serve_json(self, value: Any, status: int = 200) -> None:
            js = json.dumps(value)
            self.send_response(status)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(bytes(js, "utf8"))

        def serve_400(self) -> None:
            self.serve_text("Bad Request.", 400)
                
        def serve_404(self) -> None:
            self.serve_text("File not found.", 404)

        def get_cookies(self) -> Dict[str, str]:
            cookie_str = self.headers["Cookie"]
            if cookie_str is None:
                return {}
            return {key: value for key, value in [cookie.split("=", 1) for cookie in str(cookie_str).split("; ")]}

        def get_sess_id(self) -> Optional[str]:
            cookies = self.get_cookies()
            if "sess_id" in cookies:
                return cookies["sess_id"]
            else:
                return None
            
        def get_username(self) -> Optional[str]:
            sess_id = self.get_sess_id()
            if sess_id is not None:
                return sm.session_user(sess_id)
            else:
                return None

        def has_read_permission(self, list_name: str) -> bool:
            if list_name == 'all':
                return self.get_username() is not None
            else:
                return True

        def has_write_permission(self, list_name: str) -> bool:
            return self.get_username() is not None

        def do_GET(self) -> None:
            path = self.path.rsplit("?", 1)[0]
            spath = path.split("/")
            if len(spath) == 3 and spath[1] == "photo":
                hsh = spath[2]
                cm = cas.get_photo(hsh)
                if cm is not None:
                    contents, mime = cm
                    self.send_response(200)
                    self.send_header('Content-type', mime)
                    self.end_headers()
                    self.wfile.write(contents)
                    return
            elif len(spath) == 3 and spath[1] == "download":
                if "." in spath[2]:
                    hsh = spath[2].rsplit(".", 1)[0]
                    cm = cas.get_photo(hsh)
                    if cm is not None:
                        contents, mime = cm
                        mime = "application/octet-stream"
                        self.send_response(200)
                        self.send_header('Content-type', mime)
                        self.end_headers()
                        self.wfile.write(contents)
                    return
                else:
                    hsh = spath[2]
                    ext = cas.get_photo_extension(hsh)
                    self.send_response(301)
                    self.send_header('Location','/download/%s%s' % (hsh, ext))
                    self.end_headers()
                    return
                    
            elif len(spath) == 3 and spath[1] == 'thumb':
                hsh = spath[2]
                cm = cas.get_thumb(hsh)
                if cm is not None:
                    contents, mime = cm
                    self.send_response(200)
                    self.send_header("Content-type", mime)
                    self.end_headers()
                    self.wfile.write(contents)
                    return
            elif len(spath) == 3 and spath[1] == "list":
                list_name = urllib.parse.unquote(spath[2])
                if self.has_read_permission(list_name):
                    self.serve_json(cas.get_list(list_name))
                else:
                    self.serve_json([])
                return
            elif len(spath) == 2 and spath[1] == "albums":
                self.serve_json(cas.get_albums())
                return
            elif len(spath) == 2 and spath[1] == 'username':
                self.serve_json(self.get_username())
                return
            elif len(spath) == 2 and spath[1] == 'logout':
                sess_id = self.get_sess_id()
                if sess_id is not None:
                    sm.end_session(sess_id)
                self.serve_json(None)
                return
                    

            self.serve_static(path)
            
        def do_POST(self) -> None:
            path = self.path.rsplit("?", 1)[0]
            length_header = self.headers['Content-Length']
            if length_header is None:
                length = 0
            else:
                length = int(str(length_header))
            try:
                post_data = json.loads(self.rfile.read(length).decode('utf-8'))
            except json.JSONDecodeError:
                self.serve_400()
                return
            if path == "/download":
                try:
                    hashes = post_data['hashes']
                except KeyError:
                    self.serve_400()
                    return
                content, mime = cas.get_photos_tgz(hashes)
                self.send_response(200)
                self.send_header('Content-type', mime)
                self.end_headers()
                self.wfile.write(content)
                return
            elif path == "/add":
                try:
                    album_name = post_data['album']
                    hashes = post_data['hashes']
                except KeyError:
                    self.serve_400()
                    return
                if self.has_write_permission(album_name):
                    cas.add_photos_to_album(hashes, album_name)
                    self.send_response(201)
                    self.end_headers()
                    self.wfile.write(bytes("true", encoding="utf-8"));
                else:
                    self.send_response(403)
                    self.end_headers()
                    self.wfile.write(bytes("false", encoding="utf-8"));
                return
            elif path == "/remove":
                try:
                    album_name = post_data['album']
                    hashes = post_data['hashes']
                except KeyError:
                    self.serve_400()
                    return
                if self.has_write_permission(album_name):
                    cas.remove_photos_from_album(hashes, album_name)
                    self.send_response(201)
                    self.end_headers()
                    self.wfile.write(bytes("true", encoding="utf-8"));
                else:
                    self.send_response(403)
                    self.end_headers()
                    self.wfile.write(bytes("false", encoding="utf-8"));
                return

            elif path == "/login":
                try:
                    username = post_data['username']
                    password = post_data['password']
                except KeyError:
                    self.serve_400()
                    return
                cookie = sm.login(username, password)
                if cookie is not None:
                    self.send_response(200)
                    self.send_cookie(cookie)
                    self.end_headers()
                    self.wfile.write(bytes(username, encoding="utf-8"))
                else:
                    self.serve_text("Invalid username or password", 401)
                return
            elif path == "/passwordChange":
                try:
                    old_password = post_data['oldPassword']
                    new_password = post_data['newPassword']
                except KeyError:
                    self.serve_400()
                    return
                username = self.get_username()
                if username is None:
                    self.serve_400()
                    return
                if sm.authenticate(username, old_password):
                    sm.set_password(username, new_password)
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(bytes())
                else:
                    self.serve_text("Invalid password", 401)
                return
                

    # Server settings
    # Choose port 8080, for port 80, which is normally used for a http server, you need root access
    server_address = ('127.0.0.1', 8081)
    httpd = HTTPServer(server_address, RequestHandler)
    httpd.serve_forever()
