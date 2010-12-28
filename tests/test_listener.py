# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2010 Timothy Farrell
#
# See the included LICENSE.txt file for licensing details.

# Import System Modules
import os
import time
import socket
import unittest
import threading
try:
    import ssl
    HAS_SSL = True
except ImportError:
    HAS_SSL = False
try:
    from queue import Queue
except ImportError:
    from Queue import Queue

# Import Custom Modules
from rocket import listener

# Constants
PRIV_KEY_FILE = os.path.join(os.path.dirname(__file__), "cert_key.pem")
PUB_KEY_FILE = os.path.join(os.path.dirname(__file__), "cert.pem")


# Define Tests
class ListenerTest(unittest.TestCase):
    def setUp(self):
        self.active_queue = Queue()
        self.interface = ("127.0.0.1", 45451)
        self.has_ssl = HAS_SSL
        if HAS_SSL:
            self.secure_interface = ("127.0.0.1",
                                     45452,
                                     PRIV_KEY_FILE,
                                     PUB_KEY_FILE)
            if not os.path.exists(PRIV_KEY_FILE):
                print "Could not find private key file: "+ os.path.abspath(PRIV_KEY_FILE)
                self.has_ssl = False
            if not os.path.exists(PUB_KEY_FILE):
                print "Could not find public key file: "+ os.path.abspath(PUB_KEY_FILE)
                self.has_ssl = False



    def testReady(self):
        self.listener = listener.Listener(self.interface,
                                          5,
                                          self.active_queue)

        self.assert_(self.listener.ready)

        if self.has_ssl:
            self.sec_listener = listener.Listener(self.secure_interface,
                                                  5,
                                                  self.active_queue)
            self.assert_(self.sec_listener.ready,
                         msg="Secure listener failed to enter ready state.")

    def testNotReady(self):
        self.testReady() # create Listener

        self.listener.ready = False

        self.listener.start()

        # Give thread a chance to die
        time.sleep(0.5)

        self.assert_(not self.listener.isAlive())

    def testListen(self):
        self.testReady() # create Listener
        self.listener.start()

        self.assert_(self.listener.isAlive())

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        sock.settimeout(5)

        sock = sock.connect(self.interface)

        time.sleep(0.5)

        self.assertEqual(self.listener.active_queue.qsize(), 1)

    def testWrapSocket(self):
        if not self.has_ssl:
            print "ssl module not available"
            return

        self.testReady() # create Listener

        self.assert_(self.sec_listener.secure,
                     msg="must test on an HTTPS socket")

        sock = self.sec_listener.wrap_socket(self.sec_listener.listener)

        self.assert_(isinstance(sock, ssl.SSLSocket))

    def tearDown(self):
        try:
            self.listener.ready = False
            self.listener.join(5)
            self.assert_(not self.listener.isAlive())
        except:
            pass

        try:
            del self.listener
        except:
            pass

        if self.has_ssl:
            try:
                self.sec_listener.ready = False
                self.sec_listener.join(5)
                self.assert_(not self.sec_listener.isAlive())
            except:
                pass

            try:
                del self.sec_listener
            except:
                pass

if __name__ == '__main__':
    unittest.main()
