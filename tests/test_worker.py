# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2010 Timothy Farrell
#
# See the included LICENSE.txt file for licensing details.

# Import System Modules
import socket
import unittest
try:
    from queue import Queue
except ImportError:
    from Queue import Queue
# Import Custom Modules
from rocket import worker

class FakeConn:
    def sendall(self, data):
        if data.lower().strip().endswith("error"):
            raise socket.error
        else:
            assert data == '''\
HTTP/1.1 200 OK
Content-Length: 2
Content-Type: text/plain

OK
'''

# Define Tests
class RocketInitTest(unittest.TestCase):
    def setUp(self):
        self.worker = worker.Worker(dict(), Queue(), Queue())
        self.worker
        self.starttuple = (socket.socket(), ('127.0.0.1', 90453))
        self.serverport = 81

    def testRunApp(self):
        self.assert_(self.worker.closeConnection,
                     msg="Worker not starting with a fresh connection")
         
        self.worker.closeConnection = False
        
        self.worker.conn = FakeConn()
        
        self.assertRaises(NotImplementedError, self.worker.run_app, self.worker.conn)
        
        self.assert_(self.worker.closeConnection,
                     msg="Worker.run_app() did not set closeConnection")

    def testSendReponse(self):
        self.worker.conn = FakeConn()

        self.assert_(self.worker.closeConnection,
                     msg="Worker not starting with a fresh connection")
         
        self.worker.closeConnection = False
        
        self.worker.send_response("200 OK")
        
        self.assert_(not self.worker.closeConnection,
                     msg="Worker.send_response() set closeConnection when it shouldn't have")
        
        self.worker.closeConnection = False

        self.worker.send_response("500 Server Error")
        
        self.assert_(self.worker.closeConnection,
                     msg="Worker.send_response() did not set closeConnection when it shouldn't have")
        
    def tearDown(self):
        del self.worker
        
if __name__ == '__main__':
    unittest.main()
