# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2010 Timothy Farrell

# Import System Modules
import os
import sys
import time
import socket
import logging
import traceback
try:
    import ssl
    from ssl import SSLError
    has_ssl = True
except ImportError:
    has_ssl = False
    class SSLError(socket.error):
        pass
# Import Package Modules
from . import DEFAULTS, SERVER_SOFTWARE, IS_JYTHON, NullHandler, POLL_TIMEOUT
from .monitor import Monitor
from .threadpool import ThreadPool
from .worker import get_method
from .listener import Listener

# Setup Logging
log = logging.getLogger('Rocket')
log.addHandler(NullHandler())

class Rocket:
    """The Rocket class is responsible for handling threads and accepting and
    dispatching connections."""

    def __init__(self,
                 interfaces = ('127.0.0.1', 8000),
                 method='wsgi',
                 app_info = None,
                 min_threads=DEFAULTS['MIN_THREADS'],
                 max_threads=DEFAULTS['MAX_THREADS'],
                 queue_size = None,
                 timeout = 600,
                 handle_signals = True):

        self.handle_signals = handle_signals
        
        if not isinstance(interfaces, list):
            self.interfaces = [interfaces]
        else:
            self.interfaces = interfaces

        if not queue_size:
            if hasattr(socket, 'SOMAXCONN'):
                queue_size = socket.SOMAXCONN
            else:
                queue_size = DEFAULTS['LISTEN_QUEUE_SIZE']

        if max_threads and queue_size > max_threads:
            queue_size = max_threads

        if isinstance(app_info, dict):
            app_info['server_software'] = SERVER_SOFTWARE

        self._monitor = Monitor()
        self._threadpool = T = ThreadPool(get_method(method),
                                          app_info = app_info,
                                          min_threads=min_threads,
                                          max_threads=max_threads,
                                          timeout_queue = self._monitor.queue)

        self._monitor.out_queue = T.queue
        self._monitor.timeout = timeout

        # Build our socket listeners
        self.listeners = [Listener(i, queue_size, self._threadpool) for i in self.interfaces]
        for ndx in range(len(self.listeners)-1, 0, -1):
            if not self.listeners[ndx].ready:
                del self.listeners[ndx]

        if not self.listeners:
            log.critical("No interfaces to listen on...closing.")
            sys.exit(1)

    def start(self):
        log.info('Starting %s' % SERVER_SOFTWARE)

        # Set up our shutdown signals
        if self.handle_signals:
            try:
                import signal
                signal.signal(signal.SIGTERM, self._sigterm)
                signal.signal(signal.SIGUSR1, self._sighup)
            except:
                log.debug('This platform does not support signals.')

        # Start our worker threads
        self._threadpool.start()

        # Start our monitor thread
        self._monitor.daemon = True
        self._monitor.start()

        msg = 'Listening on sockets: '
        msg += ', '.join(['%s:%i%s' % (l.addr, l.port, '*' if l.secure else '') for l in self.listeners])
        log.info(msg)

        for l in self.listeners:
            l.start()

        while not self._threadpool.stop_server:
            try:
                self._monitor.join(POLL_TIMEOUT)
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

        for l in self.listeners:
            l.ready = False
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
