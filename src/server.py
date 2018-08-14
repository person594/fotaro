import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

from photo_store import PhotoStore
 
def run(db_path):
    ps = PhotoStore(db_path)
    class RequestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = self.path.split("/")
            print(path)
            if len(path) == 3 and path[1] == "photo":
                hsh = path[2]
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
            # Not found:
            self.send_response(404)
            self.send_header('Content-type','text/html')
            self.end_headers()

            message = "File not found."
            self.wfile.write(bytes(message, "utf8"))
            return

 
    # Server settings
    # Choose port 8080, for port 80, which is normally used for a http server, you need root access
    server_address = ('127.0.0.1', 8081)
    httpd = HTTPServer(server_address, RequestHandler)
    httpd.serve_forever()
 
 
run(sys.argv[1])
