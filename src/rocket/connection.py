# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2009 Timothy Farrell

# Import System Modules
import socket
# Import Package Modules
### None ###

class Connection(socket.socket):
    # A connection to a client
    def __init__(self, sock_tuple, port):
        self.client_addr = sock_tuple[1]
        self.server_port = port

        socket.socket.__init__(self, _sock=sock_tuple[0])

    def close(self):
        if hasattr(self, '_sock'):
            try:
                self._sock.close()
            except socket.error:
                info = sys.exc_info()
                if info[1].errno != socket.EBADF:
                    raise info[1]
                else:
                    pass
        socket.socket.close(self)
