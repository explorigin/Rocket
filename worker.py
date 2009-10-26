# -*- coding: utf-8 -*-

import os
import sys
import errno
import socket
import logging
import traceback
try: from queue import Queue
except ImportError: from Queue import Queue
from threading import Thread
from email.utils import formatdate

from . import SERVER_NAME

BUF_SIZE = 10000

ERROR_RESPONSE = '''\
HTTP/1.0 {0}
Content-Length: 0
Content-Type: text/plain

{0}
'''
HEADER_RESPONSE = '''\
HTTP/1.0 {0}
{1}
'''
py3k = sys.version_info[0] > 2

class Worker(Thread):
    # Web worker base class.
    queue = Queue()
    threads = set()
    app_info = None
    min_threads = 10
    max_threads = 10

    def run(self):
        while True:

            client, addr = self.queue.get()
            self.client, self.client_address = client, addr

            if not client:
                # A non-client is a signal to die
                return self.threads.remove(self)

            if hasattr(client,'settimeout'):
                client.settimeout(self.timeout)

            while True:
                sock_file = client.makefile('rb',BUF_SIZE)
                try:
                    data_items = self.run_app({}, sock_file)
                    if self.respond(data_items):
                        break
                except:
                    logging.warn(str(traceback.format_exc()))
                    client.sendall(ERROR_RESPONSE.format('500 Server Error').encode())
                    break

            sock_file.close()

            client.close()
            # client.close does not fully close until it is garbage collected
            # FIXME - find a way to close it NOW instead of waiting on the gc
            #del client

            self.resize_thread_pool()

    def run_app(self, environ, sock_file):
        # Must be overridden with a method that sets self.status and
        # self.headers and return an iteratable that yields bytes.
        pass

    def send_data(self, data_bytes):
        if py3k and isinstance(data_bytes, str):
            self.client.sendall(bytes(data_bytes, 'ISO-8859-1'))
        else:
            self.client.sendall(data_bytes)

    def respond(self, data_items):
        headers = self.headers
        header_dict = dict([(x.lower(),y.strip()) for (x,y) in headers])
        if not 'date' in header_dict:
            headers.append(('Date',formatdate(usegmt=True)))
        if not 'server' in header_dict:
            headers.append(('Server', SERVER_NAME))
        headers.append(('Connection','close'))
        break_loop = True
        serialized_headers = \
            ''.join(['%s: %s\r\n' % (k,v) for (k,v) in headers])
        data = HEADER_RESPONSE.format(self.status, serialized_headers)
        self.send_data(data)
        for data in data_items:
            try:
                self.send_data(data)
            except socket.error as e:
                if e.args[0] not in socket_errors_to_ignore:
                    raise
        return break_loop

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

class TestWorker(Worker):
    def run_app(self, environ, sock_file):
        first_line = sock_file.readline().decode('ISO-8859-1')
        request = first_line.split(' ')

        path_info = request[1]

        file_path = os.path.abspath(os.path.normpath(path_info))

        self.status = '200 OK'
        self.headers = [('Content-type','text/html')]
        return ['<h1>It Works!</h1>']

def get_method(method):
    from .methods.file import FileWorker
    methods = dict(file=FileWorker,
                   test=TestWorker)

    return methods.get(method.lower(), TestWorker)
