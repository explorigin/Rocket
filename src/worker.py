# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2009 Timothy Farrell

# Import System Modules
import re
import sys
import socket
import logging
import traceback
try:
    from queue import Queue
except ImportError:
    from Queue import Queue
from threading import Thread
try:
    from urllib2 import unquote
except ImportError:
    from urllib import unquote
try:
    from io import StringIO
except ImportError:
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO
# Import 3rd Party Modules
### None ###
# Import Custom Modules
from . import *
from .connection import Connection

# Define Constants
re_SLASH = re.compile('%2F', re.IGNORECASE)
ERROR_RESPONSE = '''\
HTTP/1.1 %s
Content-Length: 0
Content-Type: text/plain

%s
'''

class Worker(Thread):
    """The Worker class is a base class responsible for receiving connections
    and (a subclass) will run an application to process the the connection """

    # All of these class attributes should be correctly populated by the
    # parent thread or threadpool.
    queue = None
    app_info = None
    timeout = 1
    server_name = SERVER_NAME

    def run(self):
        self.name = self.getName()
        self.log = logging.getLogger('Rocket.%s' % self.name)
        try:
            self.log.addHandler(logging.NullHandler())
        except:
            pass
        self.log.debug('Entering main loop.')

        # Enter thread main loop
        while True:
            conn = self.queue.get()

            if isinstance(conn, tuple):
                self.pool.dynamic_resize()
                conn = Connection(*conn)

            if not conn:
                # A non-client is a signal to die
                self.log.debug('Received a death threat.')
                return

            self.conn = conn

            if IS_JYTHON:
                # In Jython we must set TCP_NODELAY here.
                # See: http://bugs.jython.org/issue1309
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

            self.log.debug('Received a connection.')

            if hasattr(conn,'settimeout') and self.timeout:
                conn.settimeout(self.timeout)

            self.closeConnection = False

            # Enter connection serve loop
            while True:
                self.log.debug('Serving a request')
                try:
                    self.run_app(conn)
                except SocketTimeout:
                    self.log.debug('Socket timed out')
                    self.wait_queue.put(conn)
                    break
                except socket.error:
                    info = sys.exc_info()
                    if info[1].errno in IGNORE_ERRORS_ON_CLOSE:
                        self.closeConnection = True
                        self.log.debug('Socket Error received...closing socket.')
                    else:
                        self.log.critical(str(traceback.format_exc()))
                except:
                    self.closeConnection = True
                    self.log.error(str(traceback.format_exc()))
                    err = ERROR_RESPONSE % ('500 Server Error', 'Server Error')
                    try:
                        conn.sendall(b(err))
                    except socket.error:
                        self.log.debug('Could not send error message.'
                                       ' Closing socket.')

                if self.closeConnection:
                    conn.close()
                    break

    def run_app(self, conn):
        # Must be overridden with a method reads the request from the socket
        # and sends a response.
        raise NotImplementedError('Overload this method!')

    def read_request_line(self, sock_file):
        try:
            # Grab the request line
            d = sock_file.readline()
            if d == b('\r\n'):
                # Allow an extra NEWLINE at the beginner per HTTP 1.1 spec
                self.log.debug('Client sent newline')
                d = sock_file.readline()
        except socket.timeout:
            raise SocketTimeout("Socket timed out before request.")

        if d == b('\r\n'):
            self.log.debug('Client sent newline again, must be closed. Raising.')
            raise socket.error('Client closed socket.')

        d = str(d.decode('latin-1'))

        try:
            method, uri, proto = d.strip().split(' ')
        except ValueError:
            # FIXME - Raise 400 Bad Request
            raise

        req = dict(method=method, protocol = proto)
        scheme = ''
        host = ''
        if uri == '*' or uri.startswith('/'):
            path = uri
        elif '://' in uri:
            scheme, rest = uri.split('://')
            host, path = rest.split('/', 1)
        else:
            path = ''

        query_string = ''
        if '?' in path:
            path, query_string = path.split('?', 1)

        path = r'%2F'.join([unquote(x) for x in re_SLASH.split(path)])

        req.update(path=path,
                   query_string=query_string,
                   scheme=scheme.lower(),
                   host=host)
        return req

    def read_headers(self, sock_file):
        headers = dict()
        l = sock_file.readline()
        lname = None
        lval = None
        while l != b('\r\n'):
            try:
                if l[0] in b(' \t') and lname:
                    # Some headers take more than one line
                    lval += u(', ') + u(l, 'latin-1').strip()
                else:
                    # HTTP header values are latin-1 encoded
                    l = l.split(b(':'), 1)
                    # HTTP header names are us-ascii encoded
                    lname = u(l[0].strip(), 'us-ascii').replace(u('-'), u('_'))
                    lname = u('HTTP_')+lname.upper()
                    lval = u(l[-1].strip(), 'latin-1')
                headers.update({str(lname): str(lval)})
            except UnicodeDecodeError:
                self.log.warning('Client sent invalid header: ' + l.__repr__())

            l = sock_file.readline()
        return headers

class SocketTimeout(Exception):
    "Exception for when a socket times out between requests."
    pass

class ChunkedReader:
    def __init__(self, sock_file):
        self.stream = sock_file
        self.buffer = None
        self.buffer_size = 0

    def _read_chunk(self):
        if not self.buffer or self.buffer.tell() == self.buffer_size:
            try:
                self.buffer_size = int(self.stream.readline().strip(), 16)
            except ValueError:
                self.buffer_size = 0

            if self.buffer_size:
                self.buffer = StringIO(self.stream.read(self.buffer_size))

    def read(self, size):
        data = b('')
        while size:
            self._read_chunk()
            if not self.buffer_size:
                break
            read_size = min(size, self.buffer_size)
            data += self.buffer.read(read_size)
            size -= read_size
        return data

    def readline(self):
        data = b('')
        c = self.read(1)
        while c != b('\n') or c == b(''):
            data += c
            c = self.read(1)
        data += c
        return data

    def readlines(self):
        yield self.readline()

class TestWorker(Worker):
    HEADER_RESPONSE = '''HTTP/1.1 %s\r\n%s\r\n'''

    def run_app(self, conn):
        self.closeConnection = True
        sock_file = conn.makefile('rb',BUF_SIZE)
        n = sock_file.readline().strip()
        while n:
            self.log.debug(n)
            n = sock_file.readline().strip()

        response = self.HEADER_RESPONSE % ('200 OK', 'Content-type: text/html')
        response += '\r\n<h1>It Works!</h1>'

        try:
            self.log.debug(response)
            conn.sendall(b(response))
        finally:
            sock_file.close()

def get_method(method):
    from .methods.wsgi import WSGIWorker
    methods = dict(test=TestWorker,
                   wsgi=WSGIWorker)

    return methods.get(method.lower(), TestWorker)
