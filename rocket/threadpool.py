# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2010 Timothy Farrell

# Import System Modules
import sys
import time
import socket
import logging
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
                 app_info,
                 active_queue,
                 monitor_queue,
                 min_threads=DEFAULTS['MIN_THREADS'],
                 max_threads=DEFAULTS['MAX_THREADS'],
                 ):

        log.debug("Initializing ThreadPool.")
        self.check_for_dead_threads = 0
        self.active_queue = active_queue

        self.worker_class = W = method
        self.min_threads = min_threads
        self.max_threads = max_threads
        self.monitor_queue = monitor_queue
        self.stop_server = False
        self.grow_threshold = int(max_threads/10) + 2

        if not isinstance(app_info, dict):
            app_info = dict()

        app_info.update(max_threads=max_threads,
                        min_threads=min_threads)

        self.threads = set()
        for x in range(min_threads):
            worker = self.worker_class(app_info,
                                       self.active_queue,
                                       self.monitor_queue)
            self.threads.add(worker)

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
            self.active_queue.put(None)

        # Give them the gun
        for t in self.threads:
            t.kill()

        # Wait until they pull the trigger
        for t in self.threads:
            t.join()

        # Clean up the mess
        self.bring_out_your_dead()

    def bring_out_your_dead(self):
        # Remove dead threads from the pool

        dead_threads = [t for t in self.threads if not t.isAlive()]
        for t in dead_threads:
            log.debug("Removing dead thread: %s." % t.getName())
            try:
                # Py2.4 complains here so we put it in a try block
                self.threads.remove(t)
            except:
                pass
        self.check_for_dead_threads -= len(dead_threads)

    def grow(self, amount=None):
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
        log.debug("Shrinking by %i." % amount)

        self.check_for_dead_threads += amount

        for x in range(amount):
            self.active_queue.put(None)

    def dynamic_resize(self):
        if (self.max_threads > self.min_threads or self.max_threads == 0):
            if self.check_for_dead_threads > 0:
                self.bring_out_your_dead()

            queueSize = self.active_queue.qsize()
            threadCount = len(self.threads)

            log.debug("Examining ThreadPool. %i threads and %i Q'd conxions"
                      % (threadCount, queueSize))

            if queueSize == 0 and threadCount > self.min_threads:
                self.shrink()

            elif queueSize > self.grow_threshold \
                 and threadCount < self.max_threads:

                self.grow(queueSize)
