# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2010 Timothy Farrell

# Import System Modules
import sys
import time
import socket
import logging
from threading import Lock
try:
    from queue import Queue
except ImportError:
    from Queue import Queue
# Import Package Modules
from . import DEFAULTS, NullHandler

# Setup Logging
log = logging.getLogger('Rocket.Errors.ThreadPool')
log.addHandler(NullHandler())

class ThreadPool:
    """The ThreadPool class is a container class for all the worker threads. It
    manages the number of actively running threads."""

    def __init__(self,
                 method,
                 min_threads=DEFAULTS['MIN_THREADS'],
                 max_threads=DEFAULTS['MAX_THREADS'],
                 app_info=None,
                 timeout_queue=None):

        log.debug("Initializing ThreadPool.")
        self.check_for_dead_threads = 0
        self.resize_lock = Lock()
        self.queue = Queue()

        self.worker_class = W = method
        self.min_threads = min_threads
        self.max_threads = max_threads
        self.timeout_queue = timeout_queue
        self.stop_server = False
        self.grow_threshold = int(max_threads/10) + 2

        if not isinstance(app_info, dict):
            app_info = dict()

        app_info.update(max_threads=max_threads,
                        min_threads=min_threads)

        W.app_info = app_info
        W.pool = self
        W.queue = self.queue
        W.wait_queue = self.timeout_queue
        W.timeout = max_threads * 0.2 if max_threads != 0 else 2

        self.threads = set([self.worker_class() for x in range(min_threads)])

    def start(self):
        self.stop_server = False
        log.debug("Starting threads.")
        for thread in self.threads:
            thread.setDaemon(True)
            thread._pool = self
            thread.start()

    def stop(self):
        log.debug("Stopping threads.")
        self.stop_server = True

        # Prompt the threads to die
        for t in self.threads:
            self.queue.put(None)

        # Give them the gun
        for t in self.threads:
            t.kill()

        # Wait until they pull the trigger
        for t in self.threads:
            t.join()

        # Clean up the mess
        self.resize_lock.acquire()
        self.bring_out_your_dead()
        self.resize_lock.release()

    def bring_out_your_dead(self):
        # Remove dead threads from the pool
        # Assumes resize_lock is acquired from calling thread

        dead_threads = [t for t in self.threads if not t.isAlive()]
        for t in dead_threads:
            log.debug("Removing dead thread: %s." % t.getName())
            self.threads.remove(t)
        self.check_for_dead_threads -= len(dead_threads)

    def grow(self, amount=None):
        # Assumes resize_lock is acquired from calling thread
        if self.stop_server:
            return

        if not amount:
            amount = self.max_threads

        amount = min([amount, self.max_threads - len(self.threads)])

        log.debug("Growing by %i." % amount)

        for x in range(amount):
            new_worker = self.worker_class()
            self.threads.add(new_worker)
            new_worker.start()

    def shrink(self, amount=1):
        # Assumes resize_lock is acquired from calling thread
        log.debug("Shrinking by %i." % amount)

        self.check_for_dead_threads += amount

        for x in range(amount):
            self.queue.put(None)

    def dynamic_resize(self):
        locked = self.resize_lock.acquire(False)
        if locked and \
           (self.max_threads > self.min_threads or self.max_threads == 0):
            if self.check_for_dead_threads > 0:
                self.bring_out_your_dead()

            queueSize = self.queue.qsize()
            threadCount = len(self.threads)

            log.debug("Examining ThreadPool. %i threads and %i Q'd conxions"
                      % (threadCount, queueSize))

            if queueSize == 0 and threadCount > self.min_threads:
                self.shrink()

            elif queueSize > self.grow_threshold \
                 and threadCount < self.max_threads:

                self.grow(queueSize)

        if locked:
            self.resize_lock.release()
