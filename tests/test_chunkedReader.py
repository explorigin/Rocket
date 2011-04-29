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
    from io import BytesIO as StringIO
except ImportError:
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO

# Import Custom Modules
from rocket import worker, b

# Constants
SAMPLE_CHUNKED_REQUEST = b('''\
25\r
This is the data in the first chunk\r
\r
1C\r
and this is the second one\r
\r
3\r
con\r
8\r
sequence\r
0\r
\r
''')
SAMPLE_CHUNKED_ANSWER = b('''\
This is the data in the first chunk\r
and this is the second one\r
consequence''')

class FakeConn:
    def sendall(self, data):
        if data.lower().strip().endswith("error"):
            raise socket.error
        else:
            assert data in SENDALL_VALUES

# Define Tests
class ChunkedReaderTest(unittest.TestCase):
    def testRead(self):
        io = StringIO(SAMPLE_CHUNKED_REQUEST)
        answer = StringIO(SAMPLE_CHUNKED_ANSWER)
        chunky = worker.ChunkedReader(io)

        res = answer.read(1)
        chk = chunky.read(1)
        while res and chk:
            self.assertEqual(res, chk)
            res = answer.read(1)
            chk = chunky.read(1)

        self.assertEqual(res, b(""))
        self.assertEqual(chk, b(""))

    def testReadLine(self):
        io = StringIO(SAMPLE_CHUNKED_REQUEST)
        answer = StringIO(SAMPLE_CHUNKED_ANSWER)
        chunky = worker.ChunkedReader(io)

        for line in answer.readlines():
            self.assertEqual(line, chunky.readline())


if __name__ == '__main__':
    unittest.main()
