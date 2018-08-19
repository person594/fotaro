import sys
import os
import json
import mimetypes
import urllib
from http.server import BaseHTTPRequestHandler, HTTPServer

from photo_store import PhotoStore
 
def run(db_path):
    ps = PhotoStore(db_path)
    class RequestHandler(BaseHTTPRequestHandler):
        def serve_static(self, path):
            print(path)
            path = os.path.normpath(path)[1:]
            print(path)
            if path == "":
                path = "view.html"
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
                # Not found
                self.send_response(404)
                self.send_header('Content-type','text/html')
                self.end_headers()
                message = "File not found."
                self.wfile.write(bytes(message, "utf8"))

        def do_GET(self):
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
                    
            elif len(spath) == 3 and spath[1] == 'thumb':
                try:
                    hsh = spath[2]
                    cm = ps.get_thumbnail(hsh)
                    if cm is not None:
                        contents, mime = cm
                        self.send_response(200)
                        self.send_header("Content-type", mime)
                        self.end_headers()
                        self.wfile.write(contents)
                        return
                except ValueError:
                    pass
            elif len(spath) == 3 and spath[1] == "list":
                list_name = spath[2]
                photo_list = ps.get_list(list_name)
                response = json.dumps(photo_list)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(bytes(response, "utf8"))
                return

            self.serve_static(path)

        def do_POST(self):
            path = self.path.rsplit("?", 1)[0]
            length = int(self.headers['Content-Length'])
            post_data = urllib.parse.parse_qs(self.rfile.read(length).decode('utf-8'))
            print(post_data)

            if path == "/download.tar.gz":
                try:
                    hashes = post_data['hashes'][0].split(",")
                    content, mime = ps.get_photos_tgz(hashes)
                    self.send_response(200)
                    self.send_header('Content-type', mime)
                    self.end_headers()
                    self.wfile.write(content)
                    return
                except KeyError:
                    pass
                
            elif path == "/add":
                ...
            

           

 
    # Server settings
    # Choose port 8080, for port 80, which is normally used for a http server, you need root access
    server_address = ('127.0.0.1', 8081)
    httpd = HTTPServer(server_address, RequestHandler)
    httpd.serve_forever()
 
 
run(sys.argv[1])
