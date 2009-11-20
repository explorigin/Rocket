# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2009 Timothy Farrell

# Import System Modules
import sys
import time
import socket
import logging
import traceback
try:
    from queue import Queue
except ImportError:
    from Queue import Queue
# Import 3rd Party Modules
### None ###
# Import Custom Modules
from . import SERVER_NAME, b, u, IS_JYTHON
from .worker import get_method

# Setup Logging
log = logging.getLogger('Rocket.ThreadPool')
try:
    log.addHandler(logging.NullHandler())
except:
    pass

class ThreadPool():
    """The ThreadPool class is a container class for all the worker threads. It
    manages the number of actively running threads."""
    # Web worker base class.
    queue = Queue()
    threads = set()

    def __init__(self,
                 method,
                 app_info=None,
                 min_threads=2,
                 max_threads=0,
                 server_name=SERVER_NAME,
                 server_port=80,
                 timeout_queue=None):

        log.debug("Initializing.")
        self.worker_class = W = get_method(method)
        self.min_threads = min_threads
        self.max_threads = max_threads
        self.timeout_queue = timeout_queue
        self.stop_server = False
        self.grow_threshold = int(max_threads/10) + 2

        if isinstance(app_info, dict):
            app_info.update(max_threads=max_threads,
                            min_threads=min_threads)

        W.app_info = app_info
        W.server_name = server_name
        W.server_port = server_port
        W.queue = self.queue
        W.wait_queue = self.timeout_queue
        W.timeout = max_threads * 0.2 if max_threads != 0 else 2

        self.threads = set([self.worker_class() for x in range(min_threads)])

    def start(self):
        log.debug("Starting threads.")
        for thread in self.threads:
            thread.daemon = True
            thread._pool = self
            thread.start()

    def stop(self):
        log.debug("Stopping threads.")
        self.stop_server = True
        break_loop = len(self.threads)

        for t in range(break_loop):
            self.queue.put((None,None))

        # For good measure
        time.sleep(0.5)

        while len(self.threads) and break_loop != 0:
            try:
                if 'client_socket' in self.threads:
                    log.debug("Shutting down client on thread")
                    self.threads.client.shutdown(socket.SHUT_RDWR)
                else:
                    break_loop -= 1
            except:
                log.warning('Failed to stop thread: \n'
                                + traceback.format_exc())
                break_loop -= 1

    def bring_out_your_dead(self):
        # Remove dead threads from the pool
        dead_threads = [t for t in self.threads if not t.is_alive()]
        for t in dead_threads:
            log.debug("Removing dead thread: %s." % t.getName())
            self.threads.remove(t)

    def grow(self, amount=None):
        if not amount:
            amount = self.max_threads
        amount = min([amount, self.max_threads - len(self.threads)])

        log.debug("Growing by %i." % amount)

        for x in range(amount):
            new_worker = self.worker_class()
            self.threads.add(new_worker)
            new_worker.start()

    def shrink(self, amount=1):
        log.debug("Shrinking by %i." % amount)

        for x in range(amount):
            self.queue.put((None, None))

    def dynamic_resize(self):
        if self.max_threads > self.min_threads or self.max_threads == 0:
            self.bring_out_your_dead()

            queueSize = self.queue.qsize()
            threadCount = len(self.threads)
            log.debug("Examining ThreadPool. %i threads and %i Q'd conxions" % (threadCount, queueSize))
            if queueSize == 0 and threadCount > self.min_threads:
                self.shrink()

            elif queueSize > self.grow_threshold and threadCount < self.max_threads:
                self.grow(queueSize)
