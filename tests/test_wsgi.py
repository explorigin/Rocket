# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2010 Timothy Farrell
#
# See the included LICENSE.txt file for licensing details.

""" test_wsgi.py tests the wsgi module against the WSGI spec as defined at:
http://www.python.org/dev/peps/pep-0333/#specification-details"""

# Import System Modules
import re
import time
import types
import socket
import unittest
import threading
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

from wsgiref.simple_server import demo_app

# Import Custom Modules
from rocket.methods import wsgi

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
    'referer': 'http://www.google.com/custom?hl=en&client=pub-9300639326172081&cof=FORID%3A13%3BAH%3Aleft%3BCX%3AUbuntu%252010%252E04%3BL%3Ahttp%3A%2F%2Fwww.google.com%2Fintl%2Fen%2Fimages%2Flogos%2Fcustom_search_logo_sm.gif%3BLH%3A30%3BLP%3A1%3BLC%3A%230000ff%3BVLC%3A%23663399%3BDIV%3A%23336699%3B&adkw=AELymgUf3P4j5tGCivvOIh-_XVcEYuoUTM3M5ETKipHcRApl8ocXgO_F5W_FOWHqlk4s4luYT_xQ10u8aDk2dEwgEYDYgHezJRTj7dx64CHnuTwPVLVChMA&channel=6911402799&q=http+request+header+sample&btnG=Search&cx=partner-pub-9300639326172081%3Ad9bbzbtli15'
}

class FakeConn:
    def __init__(self):
        self.closeConnection = True
        self.closed = False
        self.ssl = False
        self.secure = False
        self.server_port = 45454
        self.client_port = 40000
        self.client_addr = "127.0.0.1"

    def sendall(self, data):
        self.sendData = data
        if data.lower().strip().endswith("error"):
            raise socket.error

    def makefile(mode="rb", buf_size=1024):
        return StringIO('\r\n'.join(SAMPLE_HEADERS.splitlines()) + '\r\n\r\n')

    def close(self):
        self.closed = True

# Define Tests
class WSGIWorkerTest(unittest.TestCase):
    def setUp(self):
        self.active_queue = Queue()
        self.monitor_queue = Queue()
        self.app_info = {
            'server_software': 'Rocket UnitTests',
            'wsgi_app': demo_app
        }
        self.worker = wsgi.WSGIWorker(self.app_info,
                                      self.active_queue,
                                      self.monitor_queue)
        self.worker.header_set = []
        self.serverport = 45454
        self.starttuple = (socket.socket(), ('127.0.0.1', self.serverport))

        self.fakeStartCalled = False

    def fakeStart(self, a, b, c=None):
        self.fakeStartCalled = True

    def testApplicationParameters(self):
        """The application object must accept two positional arguments. For the
        sake of illustration, we have named them environ and start_response,
        but they are not required to have these names. A server or gateway must
        invoke the application object using positional (not keyword) arguments.
        (E.g. by calling result = application(environ, start_response) as shown
        above.)"""
        # Nothing to test here unless we're going to add code that tests the
        # WSGI app before the first request (which would not be a bad idea.)
        pass

    def testEnvironment(self):
        """The environ parameter is a dictionary object, containing CGI-style
        environment variables. This object must be a builtin Python dictionary
        (not a subclass, UserDict or other dictionary emulation), and the
        application is allowed to modify the dictionary in any way it desires.
        The dictionary must also include certain WSGI-required variables
        (described in a later section), and may also include server-specific
        extension variables, named according to a convention that will be
        described below."""
        REQUIRED_VARS = [
            ('REQUEST_METHOD', True, 'GET|POST|PUT|DELETE|HEAD|TRACE|OPTIONS|CONNECT'),
            ('SCRIPT_NAME', True, r'([A-Za-z][A-Za-z0-9\.\-]*)?'),
            ('PATH_INFO', True, r'([A-Za-z][A-Za-z0-9\.\-]*)?'),
            ('QUERY_STRING', False, r''),
            ('CONTENT_TYPE', False, r'\w+/\w+'),
            ('CONTENT_LENGTH', False, r'\d+'),
            ('SERVER_NAME', True, r'\w+'),
            ('SERVER_PORT', True, r'\d+'),
            ('SERVER_PROTOCOL', True, r'HTTP/1\.[01]'),
            ('wsgi.version', True, lambda x: x[0] == 1 and x[1] == 0),
            ('wsgi.url_scheme', True, r'https?'),
            ('wsgi.input', True, lambda x: hasattr(x, 'read')),
            ('wsgi.errors', True, lambda x: hasattr(x, 'read')),
            ('wsgi.multithread', True, lambda x: isinstance(x, bool)),
            ('wsgi.multiprocess', True, lambda x: isinstance(x, bool)),
            ('wsgi.run_once', True, lambda x: isinstance(x, bool)),
            ('HTTP_HOST', False, r'([A-Za-z][A-Za-z0-9\.]*)?'),
        ]
        # NOTE: We could also check other HTTP_ vars but they are browser dependent.

        self.worker.conn = conn = FakeConn()

        self.worker.conn = conn

        headersBuf = StringIO('\r\n'.join(SAMPLE_HEADERS.splitlines()) + '\r\n\r\n')
        env = self.worker.build_environ(headersBuf, conn)

        for name, reqd, validator in REQUIRED_VARS:
            if reqd:
                self.assert_(name in env,
                             msg="Missing Environment variable: " + name)
            if name in env:
                valid = validator
                if isinstance(valid, str):
                    valid = re.compile(valid)
                if isinstance(valid, (types.FunctionType, types.MethodType)):
                    self.assert_(valid(env[name]),
                                 msg="%s=\"%s\" does not validate." % (name, env[name]))
                else:
                    self.assert_(valid.match(env[name]),
                                 msg="%s=\"%s\" does not validate." % (name, env[name]))

    def testStartResponse(self):
        """The start_response parameter is a callable accepting two required
        positional arguments, and one optional argument. For the sake of
        illustration, we have named these arguments status, response_headers,
        and exc_info, but they are not required to have these names, and the
        application must invoke the start_response callable using positional
        arguments (e.g. start_response(status, response_headers)).

        The status parameter is a status string of the form "999 Message here",
        and response_headers is a list of (header_name, header_value) tuples
        describing the HTTP response header. The optional exc_info parameter is
        described below in the sections on The start_response() Callable and
        Error Handling. It is used only when the application has trapped an
        error and is attempting to display an error message to the browser.

        The start_response callable must return a write(body_data) callable
        that takes one positional parameter: a string to be written as part of
        the HTTP response body. (Note: the write() callable is provided only to
        support certain existing frameworks' imperative output APIs; it should
        not be used by new applications or frameworks if it can be avoided. See
        the Buffering and Streaming section for more details.)"""

        self.worker.conn = conn = FakeConn()
        sock_file = conn.makefile()

        self.worker.environ = environ = self.worker.build_environ(sock_file, conn)

        out = self.worker.start_response("500 Server Error",
                                         [('Content-Type', 'text/plain'),
                                          ('Content-Length', '16')])

        self.assert_(callable(out),
                     msg="WSGIWorker.start_response() did not return a callable.")

    def testApplicationReturnValueTests(self):
        """When called by the server, the application object must return an
        iterable yielding zero or more strings. This can be accomplished in a
        variety of ways, such as by returning a list of strings, or by the
        application being a generator function that yields strings, or by the
        application being a class whose instances are iterable. Regardless of
        how it is accomplished, the application object must always return an
        iterable yielding zero or more strings."""

        self.worker.conn = conn = FakeConn()
        sock_file = conn.makefile()

        self.worker.environ = environ = self.worker.build_environ(sock_file, conn)

        output = self.worker.app(environ, self.worker.start_response)

        self.assert_(hasattr(output, "__iter__") or hasattr(output, "__next__"),
                     msg="Value returned by WSGI app is not iterable")


    def testOutputHandling(self):
        """The server or gateway should treat the yielded strings as binary
        byte sequences: in particular, it should ensure that line endings are
        not altered. The application is responsible for ensuring that the
        string(s) to be written are in a format suitable for the client. (The
        server or gateway may apply HTTP transfer encodings, or perform other
        transformations for the purpose of implementing HTTP features such as
        byte-range transmission. See Other HTTP Features, below, for more
        details.)"""
        self.worker.conn = conn = FakeConn()
        sock_file = conn.makefile()

        self.worker.environ = environ = self.worker.build_environ(sock_file, conn)
        self.worker.error = (None, None)
        self.worker.headers_sent = True
        self.worker.chunked = False

        output = self.worker.app(environ, self.worker.start_response)

        for data in output:
            if data:
                self.worker.write(data, len(data))

        self.assertEqual(''.join(output), conn.sendData)

    def testReturnedValueLength(self):
        """If a call to len(iterable) succeeds, the server must be able to rely
        on the result being accurate. That is, if the iterable returned by the
        application provides a working __len__() method, it must return an
        accurate result. (See the Handling the Content-Length Header section
        for information on how this would normally be used.)"""
        # NOTE: This could be a runtime test
        pass

    def testCallCloseOnReturnedValue(self):
        """If the iterable returned by the application has a close() method,
        the server or gateway must call that method upon completion of the
        current request, whether the request was completed normally, or
        terminated early due to an error. (This is to support resource release
        by the application. This protocol is intended to complement PEP 325's
        generator support, and other common iterables with close() methods."""
        #raise NotImplementedError()
        pass

    def testStartResponseCallTiming(self):
        """Note: the application must invoke the start_response() callable
        before the iterable yields its first body string, so that the server
        can send the headers before any body content. However, this invocation
        may be performed by the iterable's first iteration, so servers must not
        assume that start_response() has been called before they begin
        iterating over the iterable.)"""
        self.worker.conn = conn = FakeConn()
        sock_file = conn.makefile()

        self.worker.environ = environ = self.worker.build_environ(sock_file, conn)
        self.worker.error = (None, None)
        self.worker.headers_sent = True
        self.worker.chunked = False

        output = self.worker.app(environ, self.fakeStart)

        temp = iter(output).next()

        self.assert_(self.fakeStartCalled,
                     msg="start_response was not called before the first iterator.")



    def testNothing(self):
        """Finally, servers and gateways must not directly use any other
        attributes of the iterable returned by the application, unless it is an
        instance of a type specific to that server or gateway, such as a "file
        wrapper" returned by wsgi.file_wrapper (see Optional Platform-Specific
        File Handling). In the general case, only attributes specified here, or
        accessed via e.g. the PEP 234 iteration APIs are acceptable."""
        # Nothing to test, just including this for completeness.
        pass

    def tearDown(self):
        del self.worker

if __name__ == '__main__':
    unittest.main()
