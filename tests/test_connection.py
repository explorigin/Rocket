# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2010 Timothy Farrell
#
# See the included LICENSE.txt file for licensing details.

# Import System Modules
import sys
import socket
import unittest
# Import Custom Modules
from rocket import connection

# Define Constants
PY3K = sys.version_info[0] > 2

# Define Tests
class RocketInitTest(unittest.TestCase):
    def setUp(self):
        self.starttuple = (socket.socket(), ('127.0.0.1', 90453))
        self.serverport = 81

    def testMembers(self):
        c = connection.Connection(self.starttuple, self.serverport)

        members = ["close", "client_addr", "server_port", "ssl", "socket", "start_time"]
        for m in members:
            self.assert_(hasattr(c, m),
                         msg="Connection object does not have {0}".format(m))

    def testClose(self):
        c = connection.Connection(self.starttuple, self.serverport)
        c.ssl = False
        def raiseError(self):
            raise RuntimeError
        c.socket._sock.close = raiseError
        self.assert_(c.socket._sock.close())

if __name__ == '__main__':
    unittest.main()
