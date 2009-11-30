# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2009 Timothy Farrell

# Import System Modules
import logging
from select import select
try:
    from queue import Queue
except ImportError:
    from Queue import Queue
from threading import Thread
# Import Package Modules
from . import IS_JYTHON

class Monitor(Thread):
    # Monitor worker base class.
    queue = Queue()
    connections = set()

    def run(self):
        self.name = self.getName()
        self.log = logging.getLogger('Rocket.Monitor')
        try:
            self.log.addHandler(logging.NullHandler())
        except:
            pass

        self.log.debug('Entering monitor loop.')

        # Enter thread main loop
        while True:
            # Move the queued connections to the selection pool
            while not self.queue.empty() or not len(self.connections):
                self.log.debug('In "receive timed-out connections" loop.')
                c = self.queue.get()

                if not c:
                    # A non-client is a signal to die
                    self.log.debug('Received a death threat.')
                    self.stop()
                    return

                self.log.debug('Received a timed out connection.')

                assert(c not in self.connections)

                if IS_JYTHON:
                    # Jython requires a socket to be in Non-blocking mode in
                    # order to select on it.
                    c.setblocking(False)

                self.log.debug('Adding connection to monitor list.')
                self.connections.add(c)

            # Wait on those connections
            self.log.debug('Blocking on connections')
            readable = select(list(self.connections), [], [], 1.0)[0]

            # If we have any readable connections, put them back
            for r in readable:
                self.log.debug('Restoring readable connection')

                if IS_JYTHON:
                    # Jython requires a socket to be in Non-blocking mode in
                    # order to select on it, but the rest of the code requires
                    # that it be in blocking mode.
                    r.setblocking(True)

                self.out_queue.put(r)
                self.connections.remove(r)

    def stop(self):
        self.log.debug('Flushing waiting connections')
        for c in self.connections:
            try:
                c.close()
            finally:
                del c

        self.log.debug('Flushing queued connections')
        while not self.queue.empty():
            c = self.queue.get()
            try:
                c.close()
            finally:
                del c
