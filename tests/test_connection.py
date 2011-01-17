# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2010 Timothy Farrell
#
# See the included LICENSE.txt file for licensing details.

# Import System Modules
import sys
import socket
import logging
import unittest
# Import Custom Modules
from rocket import Rocket, connection, SOCKET_TIMEOUT

# Constants
SERVER_PORT_START = 45450

# Define Tests
class ConnectionTest(unittest.TestCase):
    def setUp(self):
        global SERVER_PORT_START
    
        SERVER_PORT_START += 1
        self.starttuple = ('127.0.0.1', SERVER_PORT_START)

        #log = logging.getLogger('Rocket')
        #log.setLevel(logging.DEBUG)
        #fmt = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
        #h = logging.StreamHandler()
        #h.setFormatter(fmt)
        #log.addHandler(h)
        
        self.server = Rocket(self.starttuple,
                             "fs",
                             min_threads=0)
        self.server.start(background=True)

        # Create a socket connecting to listener's port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(SOCKET_TIMEOUT)
        self.sock.connect(self.starttuple)

    def tearDown(self):
        self.sock.close()
        self.server.stop()

    def testMembers(self):
        c = connection.Connection(*(self.server.active_queue.get(timeout=10)))

        members = ["close", "client_addr", "server_port", "ssl", "socket", "start_time"]
        for m in members:
            self.assert_(hasattr(c, m),
                         msg="Connection object does not have %s " % m)

    def testSocketTimeout(self):
        c = connection.Connection(*(self.server.active_queue.get(timeout=10)))

        timeout = c.socket.gettimeout()
        self.assertEqual(timeout, SOCKET_TIMEOUT)

    def testSocketRecv(self):
        c = connection.Connection(*(self.server.active_queue.get(timeout=10)))
        
        SENT_DATA = "this is a test"
        self.sock.send(SENT_DATA)
        
        data = c.recv(len(SENT_DATA))

        self.assertEqual(data, SENT_DATA)

    def testSocketSend(self):
        c = connection.Connection(*(self.server.active_queue.get(timeout=10)))
        
        RECVD_DATA = "this is a test"
        c.send(RECVD_DATA)

        data = self.sock.recv(len(RECVD_DATA))

        self.assertEqual(data, RECVD_DATA)

    # def testSocketRead(self):
        # c = connection.Connection(*(self.server.active_queue.get(timeout=10)))
        
        # SENT_DATA = "this is a test"
        # self.sock.send(SENT_DATA)
        
        # data = c.read(len(SENT_DATA))

        # self.assertEqual(data, SENT_DATA)

    # def testSocketWrite(self):
        # c = connection.Connection(*(self.server.active_queue.get(timeout=10)))
        
        # RECVD_DATA = "this is a test"
        # c.write(RECVD_DATA)

        # data = self.sock.recv(len(RECVD_DATA))

        # self.assertEqual(data, RECVD_DATA)

    # def testSocketReadline(self):
        # c = connection.Connection(*(self.server.active_queue.get(timeout=10)))
        
        # SENT_DATA = """this is a test\r\nthis is another line\r\n"""
        # self.sock.send(SENT_DATA)
        
        # for l in SENT_DATA.splitlines():
            # data = c.readline()
            # self.assertEqual(data, l+"\r\n")
    # def testSocketReadlines(self):
        # c = connection.Connection(*(self.server.active_queue.get(timeout=10)))
        
        # SENT_DATA = """this is a test\r\nthis is another line\r\n"""
        # self.sock.send(SENT_DATA)
        
        # sent_lines = SENT_DATA.splitlines()
        # read_lines = list(c.readlines())
        # self.assertEqual(sent_lines, read_lines)

if __name__ == '__main__':
    unittest.main()
