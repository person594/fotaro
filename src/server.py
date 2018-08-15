import sys
import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from photo_store import PhotoStore
 
def run(db_path):
    ps = PhotoStore(db_path)
    class RequestHandler(BaseHTTPRequestHandler):
        def serve_static(self, path):
            path = os.path.normpath(path)[1:]
            path = os.path.join("../static/", path)
            print(path)
            if os.path.isfile(path):
                with open(path, "rb") as f:
                    contents = f.read()
                self.send_response(200)
                self.send_header('Content-type','text/html')
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
            spath = self.path.split("/")
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
            elif len(spath) == 4 and spath[1] == 'small':
                try:
                    min_dim = int(spath[2])
                    hsh = spath[3]
                    cm = ps.get_scaled_photo(hsh, min_dim)
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

            self.serve_static(self.path)
           

 
    # Server settings
    # Choose port 8080, for port 80, which is normally used for a http server, you need root access
    server_address = ('127.0.0.1', 8081)
    httpd = HTTPServer(server_address, RequestHandler)
    httpd.serve_forever()
 
 
run(sys.argv[1])
