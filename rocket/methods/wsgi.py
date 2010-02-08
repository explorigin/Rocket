# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2009 Timothy Farrell

# Import System Modules
import os
import sys
import socket
from email.utils import formatdate
from wsgiref.simple_server import demo_app
from wsgiref.util import FileWrapper
# Import Package Modules
from .. import HTTP_SERVER_NAME, SERVER_NAME, b, u, BUF_SIZE, PY3K, 
from ..worker import Worker, ChunkedReader

# Define Constants
HEADER_LINE = '%s: %s\r\n'
NEWLINE = b('\r\n')
HEADER_RESPONSE = '''HTTP/1.1 %s\r\n%s\r\n'''
BASE_ENV = {'SERVER_NAME': SERVER_NAME,
            'wsgi.errors': sys.stderr,
            'wsgi.version': (1, 0),
            'wsgi.multiprocess': False,
            'wsgi.run_once': False,
            'wsgi.file_wrapper': FileWrapper
            }

class WSGIWorker(Worker):
    def __init__(self):
        """Builds some instance variables that will last the life of the
        thread."""
        if isinstance(self.app_info, dict):
            multithreaded = self.app_info.get('max_threads') != 1
        else:
            multithreaded = False
        self.base_environ = dict({'SERVER_SOFTWARE': self.server_software,
                                  'wsgi.multithread': multithreaded,
                                  })
        self.base_environ.update(BASE_ENV)
        # Grab our application
        if isinstance(self.app_info, dict):
            self.app = self.app_info.get('wsgi_app', demo_app)
        else:
            self.app = demo_app

        Worker.__init__(self)

    def build_environ(self, sock_file, conn):
        """ Build the execution environment. """
        # Grab the request line
        request = self.read_request_line(sock_file)

        # Grab the headers
        self.headers = self.read_headers(sock_file)

        # Copy the Base Environment
        environ = dict(self.base_environ)

        # Add CGI Variables
        environ['REQUEST_METHOD'] = request['method']
        # I haven't decided if we really need to be like Apache.
        #environ['REQUEST_URI'] = '?'.join((request['path'], request['query_string']))
        environ['PATH_INFO'] = request['path']
        environ['SERVER_PROTOCOL'] = request['protocol']
        environ['SCRIPT_NAME'] = '' # Direct call WSGI does not need a name
        environ['SERVER_PORT'] = str(conn.server_port)
        environ['REMOTE_PORT'] = str(conn.client_port)
        environ['REMOTE_ADDR'] = str(conn.client_addr)
        environ['QUERY_STRING'] = request['query_string']
        if 'HTTP_CONTENT_LENGTH' in self.headers:
            environ['CONTENT_LENGTH'] = self.headers['HTTP_CONTENT_LENGTH']
        if 'HTTP_CONTENT_TYPE' in self.headers:
            environ['CONTENT_TYPE'] = self.headers['HTTP_CONTENT_TYPE']

        # Save the request method for later
        self.request_method = environ['REQUEST_METHOD'].upper()

        # Add Dynamic WSGI Variables
        if conn.ssl:
            environ['wsgi.url_scheme'] = 'https'
            environ['HTTPS'] = 'on'
        else:
            environ['wsgi.url_scheme'] = 'http'
        if self.headers.get('HTTP_TRANSFER_ENCODING', '').lower() == 'chunked':
            environ['wsgi.input'] = ChunkedReader(sock_file)
        else:
            environ['wsgi.input'] = sock_file

        # Add HTTP Headers
        environ.update(self.headers)

        return environ

    def send_headers(self, data, sections):
        # Before the first output, send the stored headers
        header_dict = dict([(x.lower(), y) for (x,y) in self.header_set])

        # Does the app want us to send output chunked?
        self.chunked = header_dict.get('transfer-encoding', '').lower() == 'chunked'

        # Add a Date header if it's not there already
        if not 'date' in header_dict:
            self.header_set.append(('Date', formatdate(usegmt=True)))

        # Add a Server header if it's not there already
        if not 'server' in header_dict:
            self.header_set.append(('Server', HTTP_SERVER_SOFTWARE))

        if 'content-length' not in header_dict:
            s = int(self.status.split(' ')[0])
            if s < 200 or s not in (204, 205, 304):
                if not self.chunked:
                    if sections == 1:
                        # Add a Content-Length header if it's not there already
                        self.header_set.append(('Content-Length', len(data)))
                    else:
                        # If they sent us more than one section, we blow chunks
                        self.header_set.append(('Transfer-Encoding', 'Chunked'))
                        self.chunked = True
                        self.log.debug('Adding header...Transfer-Encoding: '
                                       'Chunked')

        # If the client or application asks to keep the connection alive, do so.
        conn = header_dict.get('connection', '').lower()
        client_conn = self.headers.get('HTTP_CONNECTION', '').lower()
        if conn != 'close' and client_conn == 'keep-alive':
            self.header_set.append(('Connection', 'keep-alive'))
            self.closeConnection = False
        else:
            self.header_set.append(('Connection', 'close'))
            self.closeConnection = True

        # Build our output headers
        serialized_headers = ''.join([HEADER_LINE % (k,v)
                                      for (k,v) in self.header_set])
        header_data = HEADER_RESPONSE % (self.status, serialized_headers)

        # Send the headers
        self.log.debug('Sending Headers: %s' % header_data.__repr__())
        self.conn.sendall(b(header_data))
        self.headers_sent = True

    def write_warning(self, data, sections=None):
        self.log.warning('WSGI app called write method directly.  This is '
                         'obsolete behavior.  Please update your app.')
        return self.write(data, sections)

    def write(self, data, sections=None):
        """ Write the data to the output socket. """

        if self.error[0]:
            self.status = self.error[0]
            data = b(self.error[1])

        if not self.headers_sent:
            self.send_headers(data, sections)

        if self.request_method != 'HEAD':
            if self.chunked:
                self.conn.sendall(b('%x\r\n' % len(data)))

            try:
                # Send another NEWLINE for good measure
                self.conn.sendall(data)
                if self.chunked:
                    self.conn.sendall(b('\r\n'))
            except socket.error:
                # But some clients will close the connection before that
                # resulting in a socket error.
                self.closeConnection = True

    def start_response(self, status, response_headers, exc_info=None):
        """ Store the HTTP status and headers to be sent when self.write is
        called. """
        if exc_info:
            try:
                if self.headers_sent:
                    # Re-raise original exception if headers sent
                    # because this violates WSGI specification.
                    raise
            finally:
                exc_info = None
        elif self.header_set:
            raise AssertionError("Headers already set!")

        if PY3K and not isinstance(status, str):
            self.status = str(status, 'ISO-8859-1')
        else:
            self.status = status
        # Make sure headers are bytes objects
        try:
            self.header_set = [(h[0].strip(),
                                h[1].strip()) for h in response_headers]
        except UnicodeDecodeError:
            self.error = ('500 Internal Server Error',
                          'HTTP Headers should be bytes')
            self.log.error('Received HTTP Headers from client that contain'
                           ' invalid characters for Latin-1 encoding.')

        return self.write_warning

    def run_app(self, conn):
        self.header_set = []
        self.headers_sent = False
        self.error = (None, None)
        sections = None
        output = None

        self.log.debug('Getting sock_file')
        # Build our file-like object
        sock_file = conn.makefile('rb',BUF_SIZE)

        try:
            # Read the headers and build our WSGI environment
            environ = self.build_environ(sock_file, conn)

            # Send it to our WSGI application
            output = self.app(environ, self.start_response)
            if not hasattr(output, '__len__') and not hasattr(output, '__iter__'):
                self.error = ('500 Internal Server Error',
                              'WSGI applications must return a list or '
                              'generator type.')

            if hasattr(output, '__len__'):
                sections = len(output)

            for data in output:
                # Don't send headers until body appears
                if data:
                    self.write(data, sections)

            # Send headers if the body was empty
            if not self.headers_sent:
                self.write(b(''))

            # If chunked, send our final chunk length
            if self.chunked:
                self.conn.sendall(b('0\r\n\r\n'))

        finally:
            self.log.debug('Finally closing output and sock_file')
            if hasattr(output,'close'):
                output.close()

            sock_file.close()
