# -*- coding: utf-8 -*-

import os
import sys
import logging
from email.utils import formatdate
from wsgiref.util import FileWrapper
from .. import HTTP_SERVER_NAME, b, u, BUF_SIZE
from ..worker import Worker

STATUS_LINE = 'Status: {0}\r\n'
HEADER_LINE = '{0}: {1}\r\n'
NEWLINE = b('\r\n')
HEADER_RESPONSE = '''HTTP/1.0 {0}\r\n{1}\r\n'''

log = logging.getLogger('Rocket.WSGI')

class WSGIWorker(Worker):
    def get_environ(self, sock_file):
        # Grab the request line
        line_one = sock_file.readline().strip().split(b(' '))

        # Grab the headers
        headers = dict()
        upper_headers = dict() # HTTP headers are not case sensitive
        l = sock_file.readline()
        while l.strip():
            l = u(l, 'ISO-8859-1').split(u(':'), 1)
            lname = u('HTTP_') + l[0].strip() # HTTP header are ISO-8859-1 encoded
            lval = l[-1].strip()
            headers.update({lname: lval})
            upper_headers.update({lname.upper():lval})

            l = sock_file.readline()

        # Start with Server Environment Variables
        environ = dict(os.environ.items())

        # Add CGI Variables
        environ['REQUEST_METHOD'] = u(line_one[0])
        environ['PATH_INFO'] = u(line_one[1])
        environ['SERVER_PROTOCOL'] = u(line_one[2])
        environ['SCRIPT_NAME'] = '' # Direct call WSGI does not need a name
        environ['SERVER_NAME'] = self.server_name
        environ['SERVER_PORT'] = self.server_port

        # Add WSGI Variables
        environ['wsgi.input'] = sock_file
        environ['wsgi.errors'] = sys.stderr
        environ['wsgi.version'] = (1,0)
        environ['wsgi.multithread'] = self.max_threads == 1
        environ['wsgi.multiprocess'] = False
        environ['wsgi.run_once'] = False
        environ['wsgi.url_scheme'] = u(line_one[2].split(b('/'))[0]).lower()
        environ['wsgi.file_wrapper'] = FileWrapper

        # Add HTTP Headers
        environ.update(headers)

        # Finish WSGI Variables
        if b('?') in line_one[1]:
            environ['QUERY_STRING'] = line_one[1].split(b('?'), 1)[-1]
        if 'HTTP_CONTENT_LENGTH' in upper_headers:
            environ['CONTENT_LENGTH'] = upper_headers['HTTP_CONTENT_LENGTH']
        if 'HTTP_CONTENT_TYPE' in upper_headers:
            environ['CONTENT_TYPE'] = upper_headers['HTTP_CONTENT_TYPE']

        self.upper_headers = upper_headers

        # DEBUG
        log.debug("Request environment: ")
        for h in environ:
            log.debug("{0}: {1}".format(h, environ[h]))

        return environ

    def run_app(self, client):
        self.header_set = []
        self.header_sent = []

        sock_file = client.makefile('rb',BUF_SIZE)

        environ = self.get_environ(sock_file)

        def write(data, sections=None):
            if not self.header_set:
                raise AssertionError("write() before start_response()")

            elif not self.header_sent:
                # Before the first output, send the stored headers
                header_dict = dict([(x.lower(), y) for (x,y) in self.header_set])
                if not b('date') in header_dict:
                    self.header_set.append(('Date',
                                             formatdate(usegmt=True)))

                if not b('server') in header_dict:
                    self.header_set.append(('Server',
                                             HTTP_SERVER_NAME))

                if not b('content-length') in header_dict and sections == 1:
                    self.header_set.append(('Content-Length', len(data)))

                # TODO - add support for chunked encoding

                # If the client asks to keep the connection alive, do so.
                # TODO - Add support for the application to determine keep-alive
                if self.upper_headers.get(u('Connection'), b('close')).lower() == b('keep-alive'):
                    self.header_set.append(('Connection', 'keep-alive'))
                    self.closeConnection = False
                else:
                    self.header_set.append(('Connection', 'close'))
                    self.closeConnection = True

                serialized_headers = ''.join([HEADER_LINE.format(k,v) for (k,v) in self.header_set])
                header_data = HEADER_RESPONSE.format(self.status, serialized_headers)
                self.client.sendall(b(header_data))
                self.client.sendall(NEWLINE)
                self.header_sent = self.header_set

            log.debug('Sending: {0}'.format(data.__repr__()))
            self.client.sendall(data)

        def start_response(status, response_headers, exc_info=None):
            if exc_info:
                try:
                    if self.header_sent:
                        # Re-raise original exception if headers sent
                        # because this violates WSGI spec.
                        raise

                finally:
                    exc_info = None
            elif self.header_set:
                raise AssertionError("Headers already set!")

            self.status = status
            self.header_set = response_headers
            return write

        if isinstance(self.app_info, dict):
            app = self.app_info.get('wsgi_app', TestApp)
        else:
            app = TestApp
        result = app(environ, start_response)
        try:
            sections = len(result)
            for data in result:
                if data:    # don't send headers until body appears
                    write(data, sections)
            if not self.header_sent:
                write('')   # send headers now if body was empty
        finally:
            if hasattr(result,'close'):
                result.close()

            sock_file.close()

def TestApp(environ, start_response):
    status = '200 OK'
    data = b('<h1>WSGI Works!</h1>')
    response_headers = [('Content-type', 'text/html')]
    start_response(status, response_headers)
    return [data]
