# -*- coding: utf-8 -*-

import os
import sys
import socket
import logging
import traceback
try: from queue import Queue
except ImportError: from Queue import Queue
from threading import Thread
try:
    from io import StringIO
except ImportError:
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO

from . import SERVER_NAME, b

ERROR_RESPONSE = '''\
HTTP/1.1 {0}
Content-Length: 0
Content-Type: text/plain

{0}
'''

class Worker(Thread):
    # Web worker base class.
    queue = Queue()
    threads = set()
    app_info = None
    min_threads = 10
    max_threads = 10
    timeout = 10
    server_name = SERVER_NAME
    server_port = 80

    def run(self):
        self.name = self.getName()
        self.log = logging.getLogger('Rocket.{0}'.format(self.name))
        try:
            self.log.addHandler(logging.NullHandler())
        except:
            pass
        self.log.debug('Entering main loop.')

        # Enter thread main loop
        while True:
            client, addr = self.queue.get()
            self.client, self.client_address = client, addr

            if not client:
                # A non-client is a signal to die
                self.log.debug('Received a death threat.')
                return self.threads.remove(self)

            self.log.debug('Received a connection.')

            if hasattr(client,'settimeout') and self.timeout:
                client.settimeout(self.timeout)

            self.closeConnection = False

            # Enter connection serve loop
            while not self.closeConnection:
                self.log.debug('Serving a request')
                try:
                    self.run_app(client)
                except socket.timeout:
                    logging.debug('Socket timed out')
                    # TODO - implement secondary queue for long-waiting sockets
                    break
                except:
                    logging.warn(str(traceback.format_exc()))
                    err = ERROR_RESPONSE.format('500 Server Error')
                    client.sendall(b(err))

            client.close()

            self.resize_thread_pool()

    def run_app(self, sock_file):
        # Must be overridden with a method reads the request from the socket
        # and sends a response.
        pass

    def resize_thread_pool(self):
        if self.max_threads > self.min_threads:
            qe = Worker.queue.empty()
            ql = len(Worker.threads)
            if qe and ql > self.min_threads:
                for k in range(self.min_threads):
                    Worker.queue.put((None,None))

            elif not qe and ql<self.max_threads:
                for k in range(self.min_threads):
                    new_worker = Worker()
                    Worker.threads.add(new_worker)
                    new_worker.start()

class ChunkedReader:
    def __init__(self, sock_file):
        self.stream = sock_file
        self.buffer = None
        self.buffer_size = 0

    def _read_chunk(self):
        if not self.buffer or self.buffer.tell() == self.buffer_size:
            try:
                self.buffer_size = int(self.stream.readline().strip(), 16)
            except ValueError:
                self.buffer_size = 0

            if self.buffer_size:
                self.buffer = StringIO(self.stream.read(self.buffer_size))

    def read(self, size):
        data = b('')
        while size:
            self._read_chunk()
            if not self.buffer_size:
                break
            read_size = min(size, self.buffer_size)
            data += self.buffer.read(read_size)
            size -= read_size
        return data

    def readline(self):
        data = b('')
        c = self.read(1)
        while c != b('\n') or c == b(''):
            data += c
            c = self.read(1)
        data += c
        return data

    def readlines(self):
        yield self.readline()

class TestWorker(Worker):
    HEADER_RESPONSE = '''HTTP/1.1 {0}\r\n{1}\r\n'''

    def run_app(self, client):
        self.closeConnection = True
        sock_file = client.makefile('rb',BUF_SIZE)
        n = sock_file.readline().strip()
        while n:
            self.log.debug(n)
            n = sock_file.readline().strip()

        response = self.HEADER_RESPONSE.format('200 OK',
                                               'Content-type: text/html')
        response += '\r\n<h1>It Works!</h1>'

        if py3k:
            response = response.encode()

        try:
            self.log.debug(response)
            client.sendall(response)
        finally:
            sock_file.close()

def get_method(method):
    from .methods.file import FileWorker
    from .methods.wsgi import WSGIWorker
    methods = dict(file=FileWorker,
                   test=TestWorker,
                   wsgi=WSGIWorker)

    return methods.get(method.lower(), TestWorker)
