# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2010 Timothy Farrell
#
# See the included LICENSE.txt file for licensing details.

""" test_wsgi.py tests the wsgi module against the WSGI spec as defined at:
http://www.python.org/dev/peps/pep-0333/#specification-details"""

# Import System Modules
import time
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
        else:
            print data
    #        assert data in SENDALL_VALUES

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
        self.serverport = 45454
        self.starttuple = (socket.socket(), ('127.0.0.1', self.serverport))

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
            'REQUEST_METHOD',
            'SCRIPT_NAME',
            'PATH_INFO',
            'QUERY_STRING',
            'CONTENT_TYPE',
            'CONTENT_LENGTH',
            'SERVER_NAME',
            'SERVER_PORT',
            'SERVER_PROTOCOL',
            'wsgi.version',
            'wsgi.url_scheme',
            'wsgi.input',
            'wsgi.errors',
            'wsgi.multithread',
            'wsgi.multiprocess',
            'wsgi.run_once'
        ]

        conn = FakeConn()

        self.worker.conn = conn

        headersBuf = StringIO('\r\n'.join(SAMPLE_HEADERS.splitlines()) + '\r\n\r\n')
        env = self.worker.build_environ(headersBuf, conn)

        for h in REQUIRED_VARS:
            self.assert_(h in env,
                         msg="Missing Environment variable: " + h)


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
        raise NotImplementedError()

    def testApplicationReturnValueTests(self):
        """When called by the server, the application object must return an
        iterable yielding zero or more strings. This can be accomplished in a
        variety of ways, such as by returning a list of strings, or by the
        application being a generator function that yields strings, or by the
        application being a class whose instances are iterable. Regardless of
        how it is accomplished, the application object must always return an
        iterable yielding zero or more strings."""
        raise NotImplementedError()

    def testOutputHandling(self):
        """The server or gateway should treat the yielded strings as binary
        byte sequences: in particular, it should ensure that line endings are
        not altered. The application is responsible for ensuring that the
        string(s) to be written are in a format suitable for the client. (The
        server or gateway may apply HTTP transfer encodings, or perform other
        transformations for the purpose of implementing HTTP features such as
        byte-range transmission. See Other HTTP Features, below, for more
        details.)"""
        raise NotImplementedError()

    def testReturnedValueLength(self):
        """If a call to len(iterable) succeeds, the server must be able to rely
        on the result being accurate. That is, if the iterable returned by the
        application provides a working __len__() method, it must return an
        accurate result. (See the Handling the Content-Length Header section
        for information on how this would normally be used.)"""
        raise NotImplementedError()

    def testCallCloseOnReturnedValue(self):
        """If the iterable returned by the application has a close() method,
        the server or gateway must call that method upon completion of the
        current request, whether the request was completed normally, or
        terminated early due to an error. (This is to support resource release
        by the application. This protocol is intended to complement PEP 325's
        generator support, and other common iterables with close() methods."""
        raise NotImplementedError()

    def testStartResponseCallTiming(self):
        """Note: the application must invoke the start_response() callable
        before the iterable yields its first body string, so that the server
        can send the headers before any body content. However, this invocation
        may be performed by the iterable's first iteration, so servers must not
        assume that start_response() has been called before they begin
        iterating over the iterable.)"""
        raise NotImplementedError()

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
