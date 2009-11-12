# -*- coding: utf-8 -*-

# Import System Modules
import os
import sys
import socket
import logging
import traceback
from select import select
try:
    from queue import Queue
except ImportError:
    from Queue import Queue
from threading import Thread
# Import 3rd Party Modules
### None ###
# Import Custom Modules
from . import SERVER_NAME, b

# Define Constants
ERROR_RESPONSE = '''\
HTTP/1.1 {0}
Content-Length: 0
Content-Type: text/plain

{0}
'''


class Monitor(Thread):
    # Monitor worker base class.
    queue = Queue()
    connections = dict()

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

            self.log.debug('Entering monitor loop.')


            # Move the queued connections to the selection pool
            while not self.queue.empty() or not len(self.connections):
                c = self.queue.get()

                if not c[0]:
                    # A non-client is a signal to die
                    self.log.debug('Received a death threat.')
                    self.stop()
                    return

                self.log.debug('Received a timed out connection.')
                if c[0] in self.connections:
                    self.log.debug('Connection received was already monitored...closing old one.')
                    self.connections[c[0]][0].close()
                    del self.connections[c[0]]

                self.log.debug('Adding connection to monitor list.')
                self.connections.update({c[0]:c})

            # Wait on those connections
            self.log.debug('Blocking on connections')
            self.log.debug(str(len(self.connections)))
            readable = select(list(self.connections.keys()), [], [], 1.0)[0]
            #readable = select([], [], [], 1.0)[0]

            # If we have any readable connections, put them back
            for x in readable:
                self.log.debug('Restoring readable connection')
                self.out_queue.put(self.connections[x])
                del self.connections[x]

    def stop(self):
        self.log.debug('Flushing waiting connections')
        for c in self.connections.items():
            try:
                c[0].close()
            finally:
                del c

        self.log.debug('Flushing queued connections')
        while not self.queue.empty():
            c = self.queue.get()
            try:
                c[0].close()
            finally:
                del c
