# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2010 Timothy Farrell
#
# See the included LICENSE.txt file for licensing details.

# Import System Modules
import time
import socket
import unittest
import threading
try:
    import ssl
    has_ssl = True
except ImportError:
    has_ssl = False
try:
    from queue import Queue
except ImportError:
    from Queue import Queue

# Import Custom Modules
from rocket import listener, worker

# Constants

# Define Tests
class ListenerTest(unittest.TestCase):
    def setUp(self):
        self.active_queue = Queue()
        self.interface = ("127.0.0.1", 45451)

    def testReady(self):
        self.listener = listener.Listener(self.interface,
                                          5,
                                          self.active_queue)

        self.assert_(self.listener.ready)

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
        if not has_ssl:
            print "ssl module not available"
            return

        self.testReady() # create Listener

        self.assert_(self.listener.secure, msg="must test on an HTTPS socket")

        sock, client = self.listener.wrap_socket((self.listener.listener, None))
        
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

if __name__ == '__main__':
    unittest.main()
