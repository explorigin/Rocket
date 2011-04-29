# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2010 Timothy Farrell
#
# See the included LICENSE.txt file for licensing details.

# Import System Modules
import time
import types
import socket
import unittest
import threading
try:
    from queue import Queue
except ImportError:
    from Queue import Queue

# Import Custom Modules
from rocket import monitor, listener, connection, threadpool, worker

# Constants
SERVER_PORT = 45454

# Define Tests
class MonitorTest(unittest.TestCase):
    def setUp(self):
        global SERVER_PORT

        SERVER_PORT += 1
        self.active_queue = Queue()
        self.monitor_queue = Queue()
        self.timeout = 10
        self.interface = ("127.0.0.1", SERVER_PORT)
        self.min_threads = 10
        self.max_threads = 20
        w = worker.Worker
        self.tp = threadpool.ThreadPool(w,
                                        dict(),
                                        self.active_queue,
                                        self.monitor_queue,
                                        self.min_threads,
                                        self.max_threads)

    def _waitForEqual(self, a, b):
        attempts = 20
        while attempts > 0:
            if isinstance(a, (types.FunctionType, types.MethodType)):
                _a = a()
            else:
                _a = a
            if isinstance(b, (types.FunctionType, types.MethodType)):
                _b = b()
            else:
                _b = b
            if _a == _b:
                return True
            time.sleep(0.25)
            attempts -= 1
        return False

    def testNotActive(self):
        self.monitor = monitor.Monitor(self.monitor_queue,
                                       self.active_queue,
                                       self.timeout,
                                       self.tp)

        self.assert_(not self.monitor.active)

    def testMonitor(self):
        self.testNotActive() # create self.monitor

        # Start the listener
        self.listener = listener.Listener(self.interface,
                                          5,
                                          self.active_queue)
        self.listener.start()

        # Create a socket connecting to listener's port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(15)
        sock.connect(self.interface)

        # Verify that listener put it in the active queue
        self._waitForEqual(self.active_queue.qsize, 1)
        self.assertEqual(self.active_queue.qsize(), 1)

        self.monitor.start()

        # Put it in the monitor queue
        conn = self.active_queue.get()
        conn = connection.Connection(*conn)
        self.monitor_queue.put(conn)
        self._waitForEqual(self.monitor_queue.qsize, 1)
        self.assertEqual(self.monitor_queue.qsize(), 1)

        # Wait for the monitor queue to see it
        self._waitForEqual(self.monitor_queue.qsize, 0)
        self.assertEqual(self.monitor_queue.qsize(), 0)

        # Send something to the socket to see if it get put back on the active
        # queue.
        sock.send("test data")

        # Give monitor a chance to see it
        self._waitForEqual(self.active_queue.qsize, 1)

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
    #import logging
    #log = logging.getLogger('Rocket')
    #log.setLevel(logging.DEBUG)
    #fmt = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
    #h = logging.StreamHandler()
    #h.setFormatter(fmt)
    #log.addHandler(h)

    unittest.main()
