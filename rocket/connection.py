# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2009 Timothy Farrell

# Import System Modules
import sys
import time
import socket
try:
    import ssl
    has_ssl = True
except ImportError:
    has_ssl = False
try:
    from io import StringIO
except ImportError:
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO

from . import IS_JYTHON, SOCKET_TIMEOUT, BUF_SIZE, b

class Connection(object):
    __slots__ = [
        'setblocking',
        'sendall',
        'shutdown',
        'makefile',
        'fileno',
        'client_addr',
        'client_port',
        'server_port',
        'socket',
        'start_time',
        'ssl',
        'secure',
        'recv',
        'send',
        'read',
        'write'
    ]

    def __init__(self, sock_tuple, port, secure=False):
        self.client_addr, self.client_port = sock_tuple[1]
        self.server_port = port
        self.socket = sock_tuple[0]
        self.start_time = time.time()
        self.ssl = has_ssl and isinstance(self.socket, ssl.SSLSocket)
        self.secure = secure

        if IS_JYTHON:
            # In Jython we must set TCP_NODELAY here since it does not
            # inherit from the listening socket.
            # See: http://bugs.jython.org/issue1309
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        self.socket.settimeout(SOCKET_TIMEOUT)

        self.sendall = self.socket.sendall
        self.shutdown = self.socket.shutdown
        self.fileno = self.socket.fileno
        self.setblocking = self.socket.setblocking
        self.recv = self.socket.recv
        self.send = self.socket.send

    def makefile(self, buf_size=BUF_SIZE):
        return FileLikeSocket(self, buf_size)

    def close(self):
        if hasattr(self.socket, '_sock'):
            try:
                self.socket._sock.close()
            except socket.error:
                info = sys.exc_info()
                if info[1].errno != socket.EBADF:
                    raise info[1]
                else:
                    pass
        self.socket.close()

class FileLikeSocket(object):
    def __init__(self, conn, buf_size=BUF_SIZE):
        self.conn = conn
        self.buf_size = buf_size
        self.buffer = StringIO()
        self.content_length = None

        if self.conn.socket.gettimeout() == 0.0:
            self.read = self.non_blocking_read
        else:
            self.read = self.blocking_read

    def __iter__(self):
        return self

    def recv(self, size):
        while True:
            try:
                return self.conn.recv(size)
            except socket.error:
                exc = sys.exc_info()
                e = exc[1]
                if (e.args[0] not in set() # socket_errors_nonblocking # FIXME
                    and e.args[0] not in set()): # socket_error_eintr): #FIXME
                    raise

    def next(self):
        data = self.readline()
        if data == '':
            raise StopIteration
        return data

    def non_blocking_read(self, size=None):
        # Shamelessly adapted from Cherrypy!
        bufr = self.buffer
        bufr.seek(0, 2)
        if size is None:
            while True:
                data = self.recv(self.buf_size)
                if not data:
                    break
                bufr.write(data)

            self.buffer = StringIO()

            return bufr.getvalue()
        else:
            buf_len = self.buffer.tell()
            if buf_len >= size:
                bufr.seek(0)
                data = bufr.read(size)
                self.buffer = StringIO(bufr.read())
                return data

            self.buffer = StringIO()
            while True:
                remaining = size - buf_len
                data = self.recv(remaining)

                if not data:
                    break

                n = len(data)
                if n == size and not buf_len:
                    return data

                if n == remaining:
                    bufr.write(data)
                    del data
                    break

                bufr.write(data)
                buf_len += n
                del data

            return bufr.getvalue()

    def blocking_read(self, length=None):
        if length is None:
            if self.content_length is not None:
                length = self.content_length
            else:
                length = 1

        try:
            data = self.conn.recv(length)
        except:
            data = b('')

        return data

    def readline(self):
        data = b("")
        char = self.read(1)
        while char != b('\n') and char is not b(''):
            line = repr(char)
            data += char
            char = self.read(1)
        data += char
        return data

    def readlines(self, hint="ignored"):
        return list(self)

    def close(self):
        self.conn = None
        self.content_length = None
