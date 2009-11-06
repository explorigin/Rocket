# -*- coding: utf-8 -*-

import os
import sys
import logging
from email.utils import formatdate
from wsgiref.util import FileWrapper
from .. import HTTP_SERVER_NAME, b, u, BUF_SIZE
from ..worker import Worker, ChunkedReader

STATUS_LINE = 'Status: {0}\r\n'
HEADER_LINE = '{0}: {1}\r\n'
NEWLINE = b('\r\n')
HEADER_RESPONSE = '''HTTP/1.1 {0}\r\n{1}\r\n'''

log = logging.getLogger('Rocket.WSGI')

class WSGIWorker(Worker):
    def get_environ(self, sock_file):
        # Grab the request line
        line_one = sock_file.readline().strip().split(b(' '))

        # Grab the headers
        headers = dict()
        lower_headers = dict() # HTTP headers are not case sensitive
        l = sock_file.readline()
        while l.strip():
            try:
                # HTTP header values are latin-1 encoded
                l = u(l, 'latin-1').split(u(':'), 1)
                # HTTP header names are us-ascii encoded
                lname = u(u('HTTP_') + l[0].strip(), 'us-ascii')
                lval = l[-1].strip()

                headers.update({lname: lval})
                lower_headers.update({lname.lower():lval})
            except UnicodeDecodeError:
                log.error('Client sent invalid header: ' + l.__repr__())

            l = sock_file.readline()

        # Start with Server Environment Variables
        environ = dict(os.environ.items())

        # Add CGI Variables
        environ['REQUEST_METHOD'] = u(line_one[0])
        environ['PATH_INFO'] = u(line_one[1], 'latin-1')
        environ['SERVER_PROTOCOL'] = u(line_one[2])
        environ['SCRIPT_NAME'] = '' # Direct call WSGI does not need a name
        environ['SERVER_NAME'] = self.server_name
        environ['SERVER_PORT'] = self.server_port

        self.request_method = environ['REQUEST_METHOD'].upper()

        # Add WSGI Variables
        environ['wsgi.errors'] = sys.stderr
        environ['wsgi.version'] = (1,0)
        environ['wsgi.multithread'] = self.max_threads == 1
        environ['wsgi.multiprocess'] = False
        environ['wsgi.run_once'] = False
        environ['wsgi.url_scheme'] = u(line_one[2].split(b('/'))[0]).lower()
        environ['wsgi.file_wrapper'] = FileWrapper

        if lower_headers.get('transfer_encoding', '').lower() == 'chunked':
            environ['wsgi.input'] = ChunkedReader(sock_file)
        else:
            environ['wsgi.input'] = sock_file

        # Add HTTP Headers
        environ.update(headers)

        # Finish WSGI Variables
        if b('?') in line_one[1]:
            environ['QUERY_STRING'] = line_one[1].split(b('?'), 1)[-1]
        if 'http_content_length' in lower_headers:
            environ['CONTENT_LENGTH'] = lower_headers['http_content_length']
        if 'http_content_type' in lower_headers:
            environ['content_type'] = lower_headers['http_content_type']

        self.lower_headers = lower_headers

        # DEBUG
        #log.debug("Request environment: ")
        #for h in environ:
        #    log.debug("{0}: {1}".format(h, environ[h]))

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

                chunked = header_dict.get(u('transfer-encoding'), '').lower()
                self.chunked = chunked == u('chunked')

                if not b('date') in header_dict:
                    self.header_set.append(('Date',
                                             formatdate(usegmt=True)))

                if not b('server') in header_dict:
                    self.header_set.append(('Server',
                                             HTTP_SERVER_NAME))

                if not b('content-length') in header_dict and not chunked:
                    if sections == 1:
                        self.header_set.append(('Content-Length', len(data)))
                    elif sections != None and section > 1:
                        self.header_set.append(('Transfer-Encoding', 'Chunked'))
                        chunked = True

                # If the client or application asks to keep the connection
                # alive, do so.
                if header_dict.get(u('connection'), '').lower() == \
                        u('keep-alive') or \
                        self.lower_headers.get(u('connection'), '').lower() ==\
                        u('keep-alive'):
                    self.header_set.append(('Connection', 'keep-alive'))
                    self.closeConnection = False
                else:
                    self.header_set.append(('Connection', 'close'))
                    self.closeConnection = True

                serialized_headers = ''.join([HEADER_LINE.format(k,v)
                                              for (k,v) in self.header_set])
                header_data = HEADER_RESPONSE.format(self.status,
                                                     serialized_headers)
                self.client.sendall(b(header_data))
                self.client.sendall(NEWLINE)
                self.header_sent = self.header_set

            log.debug('Sending Data: {0}'.format(data.__repr__()))
            if self.request_method != u('HEAD'):
                if self.chunked:
                    self.client.sendall(b('{0:x}\r\n'.format(len(data))))
                    self.client.sendall(data)
                    self.client.sendall(b('\r\n'))
                else:
                    self.client.sendall(data)

        def start_response(status, response_headers, exc_info=None):
            if exc_info:
                try:
                    if self.header_sent:
                        # Re-raise original exception if headers sent
                        # because this violates WSGI specification.
                        raise

                finally:
                    exc_info = None
            elif self.header_set:
                raise AssertionError("Headers already set!")

            self.status = status
            # Make sure headers are bytes objects
            try:
                self.header_set = [(u(h[0], 'us-ascii').strip(),
                                    u(h[1], 'latin-1').strip())
                    for h in response_headers]

            except UnicodeDecodeError:
                raise TypeError('HTTP Headers should be bytes')

            return write

        if isinstance(self.app_info, dict):
            app = self.app_info.get('wsgi_app', TestApp)
        else:
            app = TestApp
        result = app(environ, start_response)
        try:
            sections = len(result)
            for data in result:
                # Don't send headers until body appears
                if data:
                    write(data, sections)
            # If chunked, send our final chunk length
            if self.chunked:
                self.client.sendall(b('0\r\n'))
            # Send headers now if body was empty
            if not self.header_sent:
                write('')
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
