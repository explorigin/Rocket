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
from rocket import connection, SOCKET_TIMEOUT

# Define Tests
class ConnectionTest(unittest.TestCase):
    def setUp(self):
        self.starttuple = (socket.socket(), ('127.0.0.1', 30453))
        self.serverport = 81

    def testMembers(self):
        c = connection.Connection(self.starttuple, self.serverport)

        members = ["close", "client_addr", "server_port", "ssl", "socket", "start_time"]
        for m in members:
            self.assert_(hasattr(c, m),
                         msg="Connection object does not have %s " % m)

    def testSocketTimeout(self):
        c = connection.Connection(self.starttuple, self.serverport)

        timeout = c.gettimeout()
        self.assertEqual(timeout, SOCKET_TIMEOUT)

if __name__ == '__main__':
    unittest.main()
