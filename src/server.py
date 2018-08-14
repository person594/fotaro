import sys
import os
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
                print(hsh)
                pm = ps.hash_to_path_mime(hsh)
                if pm is not None:
                    photo_path, mime = pm
                    self.send_response(200)
                    self.send_header('Content-type', mime)
                    self.end_headers()
                    with open(photo_path, "rb") as f:
                        contents = f.read()
                    self.wfile.write(contents)
                    return
            else:
                self.serve_static(self.path)
           

 
    # Server settings
    # Choose port 8080, for port 80, which is normally used for a http server, you need root access
    server_address = ('127.0.0.1', 8081)
    httpd = HTTPServer(server_address, RequestHandler)
    httpd.serve_forever()
 
 
run(sys.argv[1])
