# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2009 Timothy Farrell

# Import System Modules
import os
import sys
import time
import signal
import socket
import logging
import traceback
from select import select
try:
    import ssl
except ImportError:
    ssl = None
# Import Package Modules
from . import DEFAULTS, SERVER_SOFTWARE, IS_JYTHON, NullHandler
from .monitor import Monitor
from .threadpool import ThreadPool

# Setup Logging
log = logging.getLogger('Rocket')
log.addHandler(NullHandler())

class Rocket:
    """The Rocket class is responsible for handling threads and accepting and
    dispatching connections."""

    def __init__(self,
                 interfaces = ('127.0.0.1', 8000),
                 method='test',
                 app_info = None,
                 min_threads=DEFAULTS['MIN_THREADS'],
                 max_threads=DEFAULTS['MAX_THREADS'],
                 queue_size = None,
                 timeout = 600):

        if not isinstance(interfaces, list):
            self.interfaces = [interfaces]
        else:
            self.interfaces = interfaces

        if queue_size:
            self.queue_size = queue_size
        else:
            if hasattr(socket, 'SOMAXCONN'):
                self.queue_size = socket.SOMAXCONN
            else:
                self.queue_size = DEFAULTS['LISTEN_QUEUE_SIZE']

        if max_threads and self.queue_size > max_threads:
            self.queue_size = max_threads

        self._monitor = Monitor()
        self._threadpool = T = ThreadPool(method,
                                          app_info = app_info,
                                          min_threads=min_threads,
                                          max_threads=max_threads,
                                          server_software=SERVER_SOFTWARE,
                                          timeout_queue = self._monitor.queue)

        self._monitor.out_queue = T.queue
        self._monitor.timeout = timeout

    def start(self):
        log.info('Starting %s' % SERVER_SOFTWARE)

        # Set up our shutdown signals
        try:
            signal.signal(signal.SIGTERM, self._sigterm)
            signal.signal(signal.SIGUSR1, self._sighup)
        except:
            log.debug('This platform does not support signals.')

        # Start our worker threads
        self._threadpool.start()

        # Start our monitor thread
        self._monitor.daemon = True
        self._monitor.start()

        # Build our listening sockets (with appropriate options)
        self.listeners = list()
        self.listener_dict = dict()
        for i in self.interfaces:
            addr = i[0]
            port = i[1]
            secure = len(i) > 3 and i[2] and i[3]

            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            if secure:
                if not ssl:
                    log.error("ssl module required to serve HTTPS.")
                    del listener
                    continue
                elif not os.path.exists(i[2]):
                    data = (i[2], i[0], i[1])
                    log.error("Cannot find key file "
                              "'%s'.  Cannot bind to %s:%s" % data)
                elif not os.path.exists(i[3]):
                    data = (i[3], i[0], i[1])
                    log.error("Cannot find certificate file "
                              "'%s'.  Cannot bind to %s:%s" % data)
                else:
                    listener = ssl.wrap_socket(listener,
                                               keyfile=i[2],
                                               certfile=i[3],
                                               server_side=True,
                                               ssl_version=ssl.PROTOCOL_SSLv23
                                               )

            if not listener:
                log.error("Failed to get socket.")
                raise socket.error

            try:
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            except:
                msg = "Cannot share socket.  Using %s:%i exclusively."
                log.warning(msg % (addr, port))
            try:
                if not IS_JYTHON:
                    listener.setsockopt(socket.IPPROTO_TCP,
                                        socket.TCP_NODELAY,
                                        1)
            except:
                msg = "Cannot set TCP_NODELAY, things might run a little slower"
                log.warning(msg)
            try:
                listener.bind((addr, port))
            except:
                msg = "Socket %s:%i in use by other process and it won't share."
                log.error(msg % (addr, port))
                continue

            if IS_JYTHON:
                # Jython requires a socket to be in Non-blocking mode in order
                # to select on it.
                listener.setblocking(False)

            # Listen for new connections allowing self.queue_size number of
            # connections to wait before rejecting a connection.
            listener.listen(self.queue_size)

            self.listeners.append(listener)
            self.listener_dict.update({listener: i})

        if not self.listeners:
            log.critical("No interfaces to listen on...closing.")
            sys.exit(1)

        msg = 'Listening on sockets: '
        msg += ', '.join(['%s:%i%s' % (l[0], l[1], '*' if len(l) > 2 else '') for l in self.listener_dict.values()])
        log.info(msg)

        while not self._threadpool.stop_server:
            try:
                for l in select(self.listeners, [], [], 1.0)[0]:
                    self._threadpool.queue.put((l.accept(),
                                                self.listener_dict[l][1]))
            except KeyboardInterrupt:
                # Capture a keyboard interrupt when running from a console
                return self.stop()
            except:
                if not self._threadpool.stop_server:
                    log.error(str(traceback.format_exc()))
                    continue

        if not self._threadpool.stop_server:
            self.stop()

    def _sigterm(self, signum, frame):
        log.info('Received SIGTERM')
        self.stop()

    def _sighup(self, signum, frame):
        log.info('Received SIGHUP')
        self.restart()

    def stop(self, stoplogging = True):
        log.info("Stopping Server")

        self._monitor.queue.put(None)
        self._threadpool.stop()

        self._monitor.join()
        if stoplogging:
            logging.shutdown()

    def restart(self):
        self.stop(False)
        self.start()

def CherryPyWSGIServer(bind_addr,
                       wsgi_app,
                       numthreads=10,
                       server_name=None,
                       max=-1,
                       request_queue_size=5,
                       timeout=10,
                       shutdown_timeout=5):
    """ A Cherrypy wsgiserver-compatible wrapper. """
    max_threads = max
    if max_threads < 0:
        max_threads = 0
    return Rocket(bind_addr, 'wsgi', {'wsgi_app': wsgi_app},
                  min_threads = numthreads,
                  max_threads = max_threads,
                  queue_size = request_queue_size,
                  timeout = timeout)
