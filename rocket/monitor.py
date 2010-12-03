# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2009 Timothy Farrell

# Import System Modules
import time
import logging
import select
from threading import Thread

# Import Package Modules
from . import IS_JYTHON, THREAD_STOP_CHECK_INTERVAL, NullHandler


class Monitor(Thread):
    # Monitor worker class.

    def __init__(self,
                 monitor_queue,
                 active_queue,
                 timeout,
                 *args,
                 **kwargs):

        Thread.__init__(self, *args, **kwargs)

        # Instance Variables
        self.monitor_queue = monitor_queue
        self.active_queue = active_queue
        self.timeout = timeout

        self.connections = set()
        self.active = False

    def run(self):
        self.name = self.getName()
        self.log = logging.getLogger('Rocket.Monitor')
        self.log.addHandler(NullHandler())

        self.active = True

        if __debug__:
            self.log.debug('Entering monitor loop.')

        # Enter thread main loop
        while self.active:
            # Move the queued connections to the selection pool
            while not self.monitor_queue.empty() or not len(self.connections):
                if __debug__:
                    self.log.debug('In "receive timed-out connections" loop.')

                c = self.monitor_queue.get()

                if c is None:
                    # A non-client is a signal to die
                    if __debug__:
                        self.log.debug('Received a death threat.')
                        
                    return

                self.log.debug('Received a timed out connection.')

                assert(c not in self.connections)

                if IS_JYTHON:
                    # Jython requires a socket to be in Non-blocking mode in
                    # order to select on it.
                    c.setblocking(False)

                if __debug__:
                    self.log.debug('Adding connection to monitor list.')
                    
                self.connections.add(c)

            # Wait on those connections
            self.log.debug('Blocking on connections')
            readable = select.select(list(self.connections),
                                     [], [], THREAD_STOP_CHECK_INTERVAL)[0]

            # If we have any readable connections, put them back
            for r in readable:
                if __debug__:
                    self.log.debug('Restoring readable connection')

                if IS_JYTHON:
                    # Jython requires a socket to be in Non-blocking mode in
                    # order to select on it, but the rest of the code requires
                    # that it be in blocking mode.
                    r.setblocking(True)

                r.start_time = time.time()
                self.active_queue.put(r)
                self.connections.remove(r)

            # If we have any stale connections, kill them off.
            if self.timeout:
                now = time.time()
                stale = set()
                for c in self.connections:
                    if (now - c.start_time) >= self.timeout:
                        stale.add(c)

                for c in stale:
                    if __debug__:
                        # "EXPR and A or B" kept for Py2.4 compatibility
                        data = (c.client_addr, c.server_port, c.ssl and '*' or '')
                        self.log.debug('Flushing stale connection: %s:%i%s' % data)
                        
                    self.connections.remove(c)
                    try:
                        c.close()
                    finally:
                        del c

    def stop(self):
        self.active = False

        if __debug__:
            self.log.debug('Flushing waiting connections')
            
        for c in self.connections:
            try:
                c.close()
            finally:
                del c

        if __debug__:
            self.log.debug('Flushing queued connections')
            
        while not self.monitor_queue.empty():
            c = self.monitor_queue.get()
            
            if c is None:
                continue

            try:
                c.close()
            finally:
                del c

        # Place a None sentry value to cause the monitor to die.
        self.monitor_queue.put(None)
