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
# Import Package Modules
from . import IS_JYTHON, SOCKET_TIMEOUT, BUF_SIZE, b
# TODO - This part is still very experimental.
#from .filelike import FileLikeSocket

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
        self.client_addr, self.client_port = sock_tuple[1][:2]
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

        self.shutdown = self.socket.shutdown
        self.fileno = self.socket.fileno
        self.setblocking = self.socket.setblocking
        self.recv = self.socket.recv
        self.send = self.socket.send
        self.makefile = self.socket.makefile

        if sys.platform == 'darwin':
            self.sendall = self._sendall_darwin
        else:
            self.sendall = self.socket.sendall

    def _sendall_darwin(self, buf):
        pending = len(buf)
        offset = 0
        while pending:
            try:
                sent = self.socket.send(buf[offset:])
                pending -= sent
                offset += sent
            except socket.error, e:
                if e[0]!=errno.EAGAIN:
                    raise 

# FIXME - this is not ready for prime-time yet.
#    def makefile(self, buf_size=BUF_SIZE):
#        return FileLikeSocket(self, buf_size)

    def close(self):
        if hasattr(self.socket, '_sock'):
            try:
                self.socket._sock.close()
            except socket.error:
                info = sys.exc_info()
                if info[1].args[0] != socket.EBADF:
                    raise info[1]
                else:
                    pass
        self.socket.close()

