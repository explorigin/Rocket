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
    from queue import Queue
except ImportError:
    from Queue import Queue

# Import Custom Modules
from rocket import monitor, listener, connection

# Constants

# Define Tests
class MonitorTest(unittest.TestCase):
    def setUp(self):
        self.active_queue = Queue()
        self.monitor_queue = Queue()
        self.timeout = 1
        self.interface = ("127.0.0.1", 45451)

    def testNotActive(self):
        self.monitor = monitor.Monitor(self.monitor_queue,
                                       self.active_queue,
                                       self.timeout)

        self.assert_(not self.monitor.active)

    def testMonitor(self):
        self.testNotActive() # create self.monitor
        
        self.monitor.start()
        
        # Start the listener
        self.listener = listener.Listener(self.interface,
                                          5,
                                          self.active_queue)
        self.listener.start()
        
        # Create a socket connecting to listener's port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(self.interface)

        # Verify that listener put it in the active queue
        time.sleep(0.5)
        self.assertEqual(self.active_queue.qsize(), 1)
        
        # Put it in the monitor queue
        conn = self.active_queue.get()
        conn = connection.Connection(*conn)
        self.monitor_queue.put(conn)
        self.assertEqual(self.monitor_queue.qsize(), 1)
        
        # Wait for the monitor queue to see it
        attempts = 20
        while attempts > 0 and self.monitor_queue.qsize():
            time.sleep(0.5)
            attempts -= 1
        self.assertEqual(self.monitor_queue.qsize(), 0)
        
        # Send something to the socket to see if it get put back on the active
        # queue.
        sock.send("test data")
        
        # Give monitor a chance to see it
        time.sleep(0.5)
        
        # Finally check to make sure that it's on the active queue
        self.assertEqual(self.active_queue.qsize(), 1)
        conn2 = self.active_queue.get()
        self.assert_(conn is conn2)
    
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

        try:
            self.monitor.stop()
        except:
            pass
    
        try:
            del self.monitor
        except:
            pass

if __name__ == '__main__':
    unittest.main()
