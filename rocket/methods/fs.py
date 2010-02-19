# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2010 Timothy Farrell

# Import System Modules
import os
import sys
import time
import socket
import mimetypes
from email.utils import formatdate
from wsgiref.headers import Headers
from wsgiref.util import FileWrapper
# Import Package Modules
from .. import HTTP_SERVER_SOFTWARE, b, u, BUF_SIZE
from ..worker import Worker

# Define Constants
CHUNK_SIZE = 2**16 # 64 Kilobyte chunks
HEADER_RESPONSE = '''HTTP/1.1 %s\r\n%s'''

class FileSystemWorker(Worker):
    def __init__(self):
        """Builds some instance variables that will last the life of the
        thread."""

        Worker.__init__(self)

        self.root = os.path.abspath(self.app_info['document_root'])
        self.display_index = self.app_info['display_index']
        
    def serve_file(self, filepath, headers):
        filestat = os.stat(filepath)
        self.size = filestat.st_size
        modtime = time.strftime("%a, %d %b %Y %H:%M:%S GMT",
                                time.gmtime(filestat.st_mtime))
        self.headers.add_header('Last-Modified', modtime)
        if headers.get('if_modified_since') == modtime:
            # The browser cache is up-to-date, send a 304.
            self.status = "304 Not Modified"
            self.data = []
            return
        # TODO: Implement 206 partial file support.
        ct = mimetypes.guess_type(filepath)[0]
        self.content_type = ct if ct else 'text/plain'
        try:
            f = open(filepath, 'rb')
            self.headers['Pragma'] = 'cache'
            self.headers['Cache-Control'] = 'private'
            self.headers['Content-Length'] = str(self.size)
            if self.etag:
                h.add_header('Etag', self.etag)
            if self.expires:
                h.add_header('Expires', self.expires)
            
            self.data = FileWrapper(f, CHUNK_SIZE)
        except IOError:
            self.status = "403 Forbidden"

    def serve_dir(self, pth):
        if not self.display_index:
            self.status = '404 File Not Found'
            return b('')
        else:
            self.status = '501 Not Implemented'
            return b('')

    def run_app(self, conn):
        self.status = "200 OK"
        self.size = 0
        self.expires = None
        self.etag = None
        self.content_type = 'text/plain'
        self.content_length = None

        self.err_log.debug('Getting sock_file')
        # Build our file-like object
        sock_file = conn.makefile('rb',BUF_SIZE)
        request = self.read_request_line(sock_file)
        if request['method'].upper() not in ('GET', ):
            self.status = "501 Not Implemented"
        
        try:
            # Get our file path
            headers = dict([(str(k.lower()), v) for k, v in self.read_headers(sock_file).items()])
            rpath = request.get('path', '').lstrip('/')
            filepath = os.path.join(self.root, rpath)
            filepath = os.path.abspath(filepath)
            self.err_log.debug('Request for path: %s' % filepath)
            self.closeConnection = headers.get('connection', 'close').lower() == 'close'
            self.headers = Headers([('Date', formatdate(usegmt=True)),
                                    ('Server', HTTP_SERVER_SOFTWARE),
                                    ('Connection', headers.get('connection', 'close')),
                                   ])
            
            if not filepath.lower().startswith(self.root.lower()):
                # File must be within our root directory
                self.status = "400 Bad Request"
                self.closeConnection = True
            elif not os.path.exists(filepath):
                self.status = "404 File Not Found"
                self.closeConnection = True
            elif os.path.isdir(filepath):
                self.serve_dir(filepath)
            elif os.path.isfile(filepath):
                self.serve_file(filepath, headers)
            else:
                # It exists but it's not a file or a directory????
                # What is it then?
                self.status = "501 Not Implemented"
                self.closeConnection = True

            h = self.headers
            statcode, statstr = self.status.split(' ', 1)
            statcode = int(statcode)
            if statcode >= 400:
                h.add_header('Content-Type', self.content_type)
                self.data = [statstr]
                
            # Build our output headers
            header_data = HEADER_RESPONSE % (self.status, str(h))

            # Send the headers
            self.err_log.debug('Sending Headers: %s' % repr(header_data))
            self.conn.sendall(b(header_data))
            
            for data in self.data:
                self.conn.sendall(b(data))
                
            if hasattr(self.data, 'close'):
                self.data.close()

        finally:
            self.err_log.debug('Finally closing sock_file')
            sock_file.close()
