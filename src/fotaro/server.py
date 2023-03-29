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


    def has_write_permission(self, album_name):
        # TODO!!!
        return self.fo.sm.get_username() is not None

    def daemon(self):
        self.app.run(host=self.host, port=self.port)

