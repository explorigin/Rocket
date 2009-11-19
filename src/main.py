# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2009 Timothy Farrell

# Import System Modules
import sys
import time
import signal
import socket
import logging
import traceback
from select import select
# Import 3rd Party Modules
### None ###
# Import Custom Modules
from . import SERVER_NAME, WAIT_QUEUE, IS_JYTHON
from .monitor import Monitor
from .threadpool import ThreadPool

# Setup Logging
log = logging.getLogger('Rocket')
try:
    log.addHandler(logging.NullHandler())
except:
    pass

class Rocket:
    """The Rocket class is responsible for handling threads and accepting and
    dispatching connections."""

    def __init__(self,
                 bind_addr = ('127.0.0.1', 8000),
                 method='test',
                 app_info = None,
                 max_threads = 20,
                 min_threads = 5):

        self.address = bind_addr[0]
        self.port = bind_addr[1]

        self._monitor = Monitor()
        self._threadpool = T = ThreadPool(method,
                                          app_info = app_info,
                                          min_threads=min_threads,
                                          max_threads=max_threads,
                                          server_name=SERVER_NAME,
                                          server_port=self.port,
                                          timeout_queue = self._monitor.queue)

        self._monitor.out_queue = T.queue


    def start(self):
        log.info('Starting %s' % SERVER_NAME)

        # Set up our shutdown signals
        try:
            signal.signal(signal.SIGTERM, self._sigterm)
            signal.signal(signal.SIGUSR1, self._sighup)
        except:
            log.info('This platform does not support signals.')

        # Start our worker threads
        self._threadpool.start()

        # Start our monitor thread
        self._monitor.daemon = True
        self._monitor.start()

        # Build our listening socket (with appropriate options)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if not self.socket:
            log.error("Failed to get socket.")
            raise socket.error
        try:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except:
            msg = "Cannot share socket.  Using %s:%s exclusively."
            log.warning(msg % (self.address, self.port))
        try:
            if not IS_JYTHON:
                self.socket.setsockopt(socket.IPPROTO_TCP,
                                       socket.TCP_NODELAY,
                                       1)
        except:
            msg = "Cannot set TCP_NODELAY, things might run a little slower"
            log.warning(msg)
        try:
            self.socket.bind((self.address,int(self.port)))
        except:
            msg = "Socket %s:%s in use by other process and it won't share."
            log.error(msg % (self.address, self.port))
            sys.exit(1)

        if IS_JYTHON:
            # Jython requires a socket to be in Non-blocking mode in order to
            # select on it.
            self.socket.setblocking(False)

        if hasattr(socket, 'SOMAXCONN'):
            self.socket.listen(socket.SOMAXCONN)
        else:
            # Jython goes here
            self.socket.listen(WAIT_QUEUE)

        try:
            msg = 'Listening on socket: %s:%s'
            log.info(msg % (self.address, self.port))
            while not self._threadpool.stop_server:
                try:
                    self._threadpool.dynamic_resize()
                    if select([self.socket], [], [], 1.0)[0]:
                        self._threadpool.queue.put(self.socket.accept())
                except KeyboardInterrupt:
                    return self.stop()
                except Exception:
                    log.warn(str(traceback.format_exc()))
                    continue
        except:
            log.critical("The main loop exited unexpectedly. \n"
                         + traceback.format_exc())
        return self.stop()

    def _sigterm(self):
        log.info('Received SIGTERM')
        self.stop()

    def _sighup(self):
        log.info('Received SIGHUP')
        self.restart()

    def stop(self, stoplogging = True):
        log.info("Stopping Server")

        self._monitor.queue.put((None,None))
        self._threadpool.stop()

        self._monitor.join()
        if stoplogging:
            logging.shutdown()

    def restart(self):
        self.stop(False)
        self.start()
