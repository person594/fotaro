import sys
import os
import json
import mimetypes
import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from http.cookies import BaseCookie

from photo_store import PhotoStore
from session_manager import SessionManager

def run_server(data_dir: str) -> None:
    ps = PhotoStore(data_dir)
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
            path = os.path.join("../static/", path)
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

        def serve_error(self, code: int, message: str) -> None:
            self.send_response(code)
            self.send_header('Content-type','text/html')
            self.end_headers()
            self.wfile.write(bytes(message, "utf8"))

        def serve_400(self) -> None:
            self.serve_error(400, "Bad Request.")
                
        def serve_404(self) -> None:
            self.serve_error(404, "File not found.")

        def do_GET(self) -> None:
            path = self.path.rsplit("?", 1)[0]
            spath = path.split("/")
            if len(spath) == 3 and spath[1] == "photo":
                hsh = spath[2]
                cm = ps.get_photo(hsh)
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
                    cm = ps.get_photo(hsh)
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
                    ext = ps.get_photo_extension(hsh)
                    self.send_response(301)
                    self.send_header('Location','/download/%s%s' % (hsh, ext))
                    self.end_headers()
                    return
                    
            elif len(spath) == 3 and spath[1] == 'thumb':
                hsh = spath[2]
                cm = ps.get_thumbnail(hsh)
                if cm is not None:
                    contents, mime = cm
                    self.send_response(200)
                    self.send_header("Content-type", mime)
                    self.end_headers()
                    self.wfile.write(contents)
                    return
            elif len(spath) == 3 and spath[1] == "list":
                list_name = urllib.parse.unquote(spath[2])
                photo_list = ps.get_list(list_name)
                response = json.dumps(photo_list)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(bytes(response, "utf8"))
                return
            elif len(spath) == 2 and spath[1] == "albums":
                albums = ps.get_albums()
                response = json.dumps(albums)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(bytes(response, "utf8"))
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
                content, mime = ps.get_photos_tgz(hashes)
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
                ps.add_photos_to_album(hashes, album_name)
                self.send_response(201)
                self.end_headers()
                self.wfile.write(bytes("true", encoding="utf-8"));
                return
            elif path == "/remove":
                try:
                    album_name = post_data['album']
                    hashes = post_data['hashes']
                except KeyError:
                    self.serve_400()
                    return
                ps.remove_photos_from_album(hashes, album_name)
                self.send_response(201)
                self.end_headers()
                self.wfile.write(bytes("true", encoding="utf-8"));
                return

            elif path == "/login":
                try:
                    username= post_data['username']
                    password = post_data['password']
                except KeyError:
                    self.serve_400()
                    return
                cookie = sm.authenticate(username, password)
                if cookie is not None:
                    self.send_response(200)
                    self.send_cookie(cookie)
                    self.end_headers()
                    self.wfile.write(bytes("true", encoding="utf-8"))
                else:
                    self.serve_error(401, "Invalid username or password")
                return
  

    # Server settings
    # Choose port 8080, for port 80, which is normally used for a http server, you need root access
    server_address = ('127.0.0.1', 8081)
    httpd = HTTPServer(server_address, RequestHandler)
    httpd.serve_forever()
