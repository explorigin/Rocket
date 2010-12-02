# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2010 Timothy Farrell

# Import System Modules
import re
import sys
import socket
import logging
import traceback
from wsgiref.headers import Headers
from threading import Thread
from datetime import datetime

try:
    from urllib import unquote
except ImportError:
    from urllib.parse import unquote

try:
    from io import StringIO
except ImportError:
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO

try:
    from ssl import SSLError
except ImportError:
    class SSLError(socket.error):
        pass
# Import Package Modules
from . import IGNORE_ERRORS_ON_CLOSE, b, PY3K, NullHandler
from .connection import Connection

# Define Constants
re_SLASH = re.compile('%2F', re.IGNORECASE)
LOG_LINE = '%(client_ip)s - "%(request_line)s" - %(status)s %(size)s'
RESPONSE = '''\
HTTP/1.1 %s
Content-Length: %i
Content-Type: %s

%s
'''

class Worker(Thread):
    """The Worker class is a base class responsible for receiving connections
    and (a subclass) will run an application to process the the connection """

    def __init__(self,
                 app_info,
                 active_queue,
                 monitor_queue,
                 *args,
                 **kwargs):

        Thread.__init__(self, *args, **kwargs)

        # Instance Variables
        self.app_info = app_info
        self.active_queue = active_queue
        self.monitor_queue = monitor_queue

        # Request Log
        self.req_log = logging.getLogger('Rocket.Requests')
        self.req_log.addHandler(NullHandler())

        # Error Log
        self.err_log = logging.getLogger('Rocket.Errors.'+self.getName())
        self.err_log.addHandler(NullHandler())

    def _handleError(self, typ, val, tb):
        if typ == SSLError:
            if 'timed out' in val.args[0]:
                typ = SocketTimeout
        if typ == SocketTimeout:
            self.err_log.debug('Socket timed out')
            self.monitor_queue.put(self.conn)
            return True
        if typ == SocketClosed:
            self.closeConnection = True
            self.err_log.debug('Client closed socket')
            return False
        if typ == BadRequest:
            self.closeConnection = True
            self.err_log.debug('Client sent a bad request')
            return True
        if typ == socket.error:
            self.closeConnection = True
            if val.args[0] in IGNORE_ERRORS_ON_CLOSE:
                self.closeConnection = True
                self.err_log.debug('Ignorable socket Error received...'
                                   'closing connection.')
                return False
            else:
                self.status = "999 Utter Server Failure"
                tb = traceback.format_exception((typ, val, tb))
                self.err_log.error('Unhandled Error when serving '
                                   'connection:\n' + tb)
                return False

        self.closeConnection = True
        self.err_log.error(str(traceback.format_exc()))
        self.send_response('500 Server Error')
        return False

    def run(self):
        self.err_log.debug('Entering main loop.')

        # Enter thread main loop
        while True:
            conn = self.active_queue.get()

            if not conn:
                # A non-client is a signal to die
                self.err_log.debug('Received a death threat.')
                return

            if isinstance(conn, tuple):
                conn = Connection(*conn)

            self.conn = conn

            if conn.ssl != conn.secure:
                self.err_log.info('Received HTTP connection on HTTPS port.')
                self.send_response('400 Bad Request')
                self.closeConnection = True
                conn.close()
                continue
            else:
                self.err_log.debug('Received a connection.')
                self.closeConnection = False

            # Enter connection serve loop
            while True:
                self.err_log.debug('Serving a request')
                try:
                    self.run_app(conn)
                    log_info = dict(client_ip = conn.client_addr,
                                    time = datetime.now().strftime('%c'),
                                    status = self.status.split(' ')[0],
                                    size = self.size,
                                    request_line = self.request_line)
                    self.req_log.info(LOG_LINE % log_info)
                except:
                    exc = sys.exc_info()
                    handled = self._handleError(*exc)
                    if handled:
                        break
                    else:
                        if self.request_line:
                            log_info = dict(client_ip = conn.client_addr,
                                            time = datetime.now().strftime('%c'),
                                            status = self.status.split(' ')[0],
                                            size = self.size,
                                            request_line = self.request_line + ' - not stopping')
                            self.req_log.info(LOG_LINE % log_info)

                if self.closeConnection:
                    try:
                        conn.close()
                    except:
                        self.err_log.error(str(traceback.format_exc()))

                    break

    def run_app(self, conn):
        # Must be overridden with a method reads the request from the socket
        # and sends a response.
        self.closeConnection = True
        raise NotImplementedError('Overload this method!')

    def send_response(self, status):
        msg = RESPONSE % (status,
                          len(status),
                          'text/plain',
                          status.split(' ', 1)[1])
        try:
            self.conn.sendall(b(msg))
        except socket.error:
            self.closeConnection = True
            self.err_log.error('Tried to send "%s" to client but received socket'
                           ' error' % status)

    def kill(self):
        if self.isAlive() and hasattr(self, 'conn'):
            try:
                self.conn.shutdown(socket.SHUT_RDWR)
            except socket.error:
                info = sys.exc_info()
                if info[1].args[0] != socket.EBADF:
                    self.err_log.debug('Error on shutdown: '+str(info))

    def read_request_line(self, sock_file):
        self.request_line = ''
        try:
            # Grab the request line
            d = sock_file.readline()
            if PY3K:
                d = d.decode('ISO-8859-1')

            if d == '\r\n':
                # Allow an extra NEWLINE at the beginner per HTTP 1.1 spec
                self.err_log.debug('Client sent newline')
                d = sock_file.readline()
                if PY3K:
                    d = d.decode('ISO-8859-1')
        except socket.timeout:
            raise SocketTimeout("Socket timed out before request.")

        if d.strip() == '':
            self.err_log.debug('Client did not send a recognizable request.')
            raise SocketClosed('Client closed socket.')

        try:
            self.request_line = d.strip()
            method, uri, proto = self.request_line.split(' ')
            assert proto.startswith('HTTP')
        except ValueError:
            self.send_response('400 Bad Request')
            raise BadRequest
        except AssertionError:
            self.send_response('400 Bad Request')
            raise BadRequest

        req = dict(method=method, protocol = proto)
        scheme = ''
        host = ''
        if uri == '*' or uri.startswith('/'):
            path = uri
        elif '://' in uri:
            scheme, rest = uri.split('://')
            host, path = rest.split('/', 1)
        else:
            self.send_response('400 Bad Request')
            raise BadRequest

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
        headers = Headers([])
        l = sock_file.readline()

        lname = None
        lval = None
        while True:
            try:
                if PY3K:
                    l = str(l, 'ISO-8859-1')
            except UnicodeDecodeError:
                self.err_log.warning('Client sent invalid header: ' + repr(l))

            if l == '\r\n':
                break

            if l[0] in ' \t' and lname:
                # Some headers take more than one line
                lval += ', ' + l.strip()
            else:
                # HTTP header values are latin-1 encoded
                l = l.split(':', 1)
                # HTTP header names are us-ascii encoded
                lname = l[0].strip().replace('-', '_')
                lval = l[-1].strip()
            headers[str(lname)] = str(lval)

            l = sock_file.readline()
        return headers

class SocketTimeout(Exception):
    "Exception for when a socket times out between requests."
    pass

class BadRequest(Exception):
    "Exception for when a client sends an incomprehensible request."
    pass

class SocketClosed(Exception):
    "Exception for when a socket is closed by the client."
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

def get_method(method):
    from .methods.wsgi import WSGIWorker
    from .methods.fs import FileSystemWorker
    methods = dict(wsgi=WSGIWorker,
                   fs=FileSystemWorker)
    return methods[method.lower()]
