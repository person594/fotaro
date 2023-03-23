import sys
import os
import json
import mimetypes
import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from http.cookies import BaseCookie
import importlib.resources
import pathlib
from typing import Optional, Dict, Any, List

from flask import Flask, send_file, send_from_directory, abort, render_template, request, make_response, jsonify

import jinja2
from jinja2 import Environment, PackageLoader, select_autoescape

from .util import unflatten_dict

from .component import Component

class Server(Component):
    def __init__(self, fo,
                 host: str = '',
                 port: int = 8081
                 ):
        self.fo = fo
        self.host = host
        self.port = port
        self.app = Flask(__name__)

        self.route = self.app.route

    def setup(self):
        
        @self.route('/', defaults={'path': 'photos.html'})
        @self.route('/<path:path>')
        def serve_template(path):
            try:
                return render_template(path, fo=self.fo)
            except jinja2.exceptions.TemplateNotFound:
                return send_from_directory("static", path)
        
        @self.route("/photo/<hsh>")
        def serve_photo(hsh):
            try:
                photo = self.fo.cas[hsh]
            except IndexError:
                abort(404)
            extension = mimetypes.guess_extension(photo.mime)
            dl_name = hsh + extension
            return send_file(photo.path, mimetype=photo.mime, download_name=dl_name)

        @self.route("/thumb/<hsh>")
        def serve_thumbnail(hsh):
            try:
                photo = self.fo.cas[hsh]
            except IndexError:
                abort(404)
            extension = mimetypes.guess_extension(photo.thumb_mime)
            dl_name = 'thumb_' + hsh + extension
            return send_file(photo.thumb_path, mimetype=photo.thumb_mime, download_name=dl_name)

        @self.route("/download/<hsh>")
        def serve_download(hsh):
            try:
                photo = self.fo.cas[hsh]
            except IndexError:
                abort(404)
            extension = mimetypes.guess_extension(photo.mime)
            dl_name = hsh + extension
            return send_file(photo.path, as_attachment=True, mimetype=photo.mime, download_name=dl_name)

        @self.route("/download", methods=["POST"])
        def serve_download_post():
            try:
                hashes = request.json['hashes']
            except KeyError:
                abort(400)
            content, mime = self.fo.cas.get_photos_tgz(hashes)
            resp = make_response(content)
            resp.headers.set('Content-Type', mime)
            resp.headers.set('Content-Disposition', 'attachment', filename='download.tar.gz')
            return resp

        @self.route("/add", methods=["POST"])
        def serve_add():
            try:
                album_name = request.json['album']
                hashes = request.json['hashes']
            except KeyError:
                abort(400)
            if self.has_write_permission(album_name):
                self.fo.add_photos_to_album(hashes, album_name)
                return jsonify(True), 201
            else:
                return jsonify(False), 403

        @self.route("/remove", methods=["POST"])
        def serve_remove():
            try:
                album_name = request.json['album']
                hashes = request.json['hashes']
            except KeyError:
                abort(400)
            if self.has_write_permission(album_name):
                self.fo.remove_photos_from_album(hashes, album_name)
                return jsonify(True), 201
            else:
                return jsonify(False), 403
        
        @self.route("/list/<listname>")
        def serve_list(listname):
            return list(self.fo.get_list(listname))

        @self.route("/albums")
        def serve_albums():
            return self.fo.get_albums()


    def get_username(self):
        sess_id = request.cookies.get('sess_id')
        if sess_id is None:
            return None
        return self.fo.sm.session_user(sess_id)

    def has_write_permission(self, album_name):
        # TODO!!!
        return self.get_username() is not None

    def daemon(self):
        self.app.run(host=self.host, port=self.port)
        print("Hello")
        exit()
        fo = self.fo
        class RequestHandler(BaseHTTPRequestHandler):
            def send_cookie(self, c: BaseCookie) -> None:
                for key in c:
                    self.send_header('Set-Cookie', c[key].output(header=''))

            def serve_template(self, path: str) -> None:
                template = env.get_template(path)
                contents = template.render(fo=fo)
                contents = bytes(contents, 'utf-8')
                self.send_response(200)
                mime, _ = mimetypes.guess_type(path)
                if mime is None:
                    mime = "application/octet-stream"
                self.send_header('Content-type', mime)
                self.end_headers()
                self.wfile.write(contents)




            def serve_static(self, path: str) -> None:
                parts = pathlib.Path(path).parts
                dotpath = '.'.join(('fotaro', 'data', 'static') + parts[:-1])
                resource = parts[-1]
                if importlib.resources.is_resource(dotpath, resource):
                    contents = importlib.resources.read_binary(dotpath, resource)
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
                    return fo.sm.session_user(sess_id)
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
                    cm = fo.cas.get_photo(hsh)
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
                        cm = fo.cas.get_photo(hsh)
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
                        ext = fo.cas.get_photo_extension(hsh)
                        self.send_response(301)
                        self.send_header('Location','/download/%s%s' % (hsh, ext))
                        self.end_headers()
                        return

                elif len(spath) == 3 and spath[1] == 'thumb':
                    hsh = spath[2]
                    cm = fo.cas.get_thumb(hsh)
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
                        self.serve_json(fo.get_list(list_name))
                    else:
                        self.serve_json([])
                    return
                elif len(spath) == 2 and spath[1] == "albums":
                    self.serve_json(fo.get_albums())
                    return
                elif len(spath) == 2 and spath[1] == 'username':
                    self.serve_json(self.get_username())
                    return
                elif len(spath) == 2 and spath[1] == 'logout':
                    sess_id = self.get_sess_id()
                    if sess_id is not None:
                        fo.sm.end_session(sess_id)
                    self.serve_json(None)
                    return

                # we are serving a file; make sure the path looks like a path to a file
                path = os.path.normpath(path)[1:]
                if path == "":
                    path = "photos.html"
                if "." not in path:
                    path = path + ".html"

                try:
                    self.serve_template(path)
                except jinja2.exceptions.TemplateNotFound:
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
                    content, mime = fo.cas.get_photos_tgz(hashes)
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
                        fo.add_photos_to_album(hashes, album_name)
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
                        fo.remove_photos_from_album(hashes, album_name)
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
                    cookie = fo.sm.login(username, password)
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
                    if fo.sm.authenticate(username, old_password):
                        fo.sm.set_password(username, new_password)
                        self.send_response(200)
                        self.end_headers()
                        self.wfile.write(bytes())
                    else:
                        self.serve_text("Invalid password", 401)
                    return
                elif path == "/search":
                    post_data = unflatten_dict(post_data)
                    breakpoint()
                    try:
                        search_list = post_data['list']
                    except KeyError:
                        self.serve_400()
                    if self.has_read_permission(search_list):
                        sort_by = None
                        for sb in fo.get_sort_bys():
                            if sb.name == post_data['sortBy']:
                                sort_by = sb
                                break
                        self.serve_json(fo.get_search_results(search_list, [], sort_by))
                    else:
                        self.serve_json([])


        # Server settings
        # Choose port 8080, for port 80, which is normally used for a http server, you need root access
        server_address = (self.host, self.port)
        httpd = HTTPServer(server_address, RequestHandler)
        httpd.serve_forever()
