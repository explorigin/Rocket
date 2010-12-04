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

try:
    from io import StringIO
except ImportError:
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO

# Import Custom Modules
from rocket import worker

# Constants
SAMPLE_HEADERS = '''\
GET /dumprequest HTTP/1.1
Host: djce.org.uk
User-Agent: Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.12) Gecko/20101027 Ubuntu/10.04 (lucid) Firefox/3.6.12
Accept: text/html,application/xhtml+xml
 application/xml;q=0.9,*/*;q=0.8
Accept-Language: en-us,en;q=0.5
Accept-Encoding: gzip,deflate
Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7
Keep-Alive: 115
Connection: keep-alive
Referer: http://www.google.com/custom?hl=en&client=pub-9300639326172081&cof=FORID%3A13%3BAH%3Aleft%3BCX%3AUbuntu%252010%252E04%3BL%3Ahttp%3A%2F%2Fwww.google.com%2Fintl%2Fen%2Fimages%2Flogos%2Fcustom_search_logo_sm.gif%3BLH%3A30%3BLP%3A1%3BLC%3A%230000ff%3BVLC%3A%23663399%3BDIV%3A%23336699%3B&adkw=AELymgUf3P4j5tGCivvOIh-_XVcEYuoUTM3M5ETKipHcRApl8ocXgO_F5W_FOWHqlk4s4luYT_xQ10u8aDk2dEwgEYDYgHezJRTj7dx64CHnuTwPVLVChMA&channel=6911402799&q=http+request+header+sample&btnG=Search&cx=partner-pub-9300639326172081%3Ad9bbzbtli15'''
HEADER_DICT = {
    'host': 'djce.org.uk',
    'user_agent': 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.12) Gecko/20101027 Ubuntu/10.04 (lucid) Firefox/3.6.12',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'accept_language': 'en-us,en;q=0.5',
    'accept_encoding': 'gzip,deflate',
    'accept_charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
    'keep_alive': '115',
    'connection': 'keep-alive',
    'referer': 'http://www.google.com/custom?hl=en&client=pub-9300639326172081&cof=FORID%3A13%3BAH%3Aleft%3BCX%3AUbuntu%252010%252E04%3BL%3Ahttp%3A%2F%2Fwww.google.com%2Fintl%2Fen%2Fimages%2Flogos%2Fcustom_search_logo_sm.gif%3BLH%3A30%3BLP%3A1%3BLC%3A%230000ff%3BVLC%3A%23663399%3BDIV%3A%23336699%3B&adkw=AELymgUf3P4j5tGCivvOIh-_XVcEYuoUTM3M5ETKipHcRApl8ocXgO_F5W_FOWHqlk4s4luYT_xQ10u8aDk2dEwgEYDYgHezJRTj7dx64CHnuTwPVLVChMA&channel=6911402799&q=http+request+header+sample&btnG=Search&cx=partner-pub-9300639326172081%3Ad9bbzbtli15'}
SENDALL_HEADER_TEMPLATE = '''HTTP/1.1 200 OK\nContent-Length: 2
Content-Type: text/plain\n\nOK\n'''


class FakeConn:
    def sendall(self, data):
        if data.lower().strip().endswith("error"):
            raise socket.error
        else:
            assert data == SENDALL_HEADER_TEMPLATE

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

    def testReadHeaders(self):
        headersBuf = StringIO('\r\n'.join(SAMPLE_HEADERS.splitlines()[1:]) + '\r\n\r\n')
        headers = self.worker.read_headers(headersBuf)

        for header_name in HEADER_DICT.keys():
            self.assertEqual(headers[header_name], HEADER_DICT[header_name])

    def tearDown(self):
        del self.worker

if __name__ == '__main__':
    unittest.main()
