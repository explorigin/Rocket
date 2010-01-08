# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2009 Timothy Farrell

# Import System Modules
import time
import socket
try:
    import ssl
except ImportError:
    ssl = None
# Import Package Modules
from . import PY3K

class Connection:
    def __init__(self, sock_tuple, port):
        self.client_addr, self.client_port = sock_tuple[1]
        self.server_port = port
        self.socket = sock_tuple[0]
        self.start_time = time.time()
        self.ssl = ssl and isinstance(self.socket, ssl.SSLSocket)

        for x in dir(self.socket):
            if not hasattr(self, x):
                try:
                    self.__dict__[x] = self.socket.__getattribute__(x)
                except:
                    pass

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
