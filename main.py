# -*- coding: utf-8 -*-

import sys
import time
import signal
import socket
import logging
import traceback
from select import select

from . import SERVER_NAME

log = logging.getLogger('Rocket')
try:
    log.addHandler(logging.NullHandler())
except:
    pass

from .worker import get_method

class Rocket:
    """The Rocket class is responsible for handling threads and receiving and
    dispatching connections."""

    def __init__(self,
                 bind_addr = ('127.0.0.1', 8000),
                 method='test',
                 app_info = None,
                 max_threads = 0,
                 min_threads = 10):

        self.address = bind_addr[0]
        self.port = bind_addr[1]

        self._worker = W = get_method(method)

        W.app_info = app_info
        W.server_name = SERVER_NAME
        W.server_port = self.port
        W.stopServer = False
        W.min_threads = min_threads
        W.max_threads = max_threads
        W.timeout = max_threads * 0.2
        W.threads = set([W() for k in range(min_threads)])

    def start(self):
        msg = 'Starting {0}'
        log.info(msg.format(SERVER_NAME))

        # Set up our shutdown signals
        try:
            signal.signal(signal.SIGTERM, self._sigterm)
            signal.signal(signal.SIGUSR1, self._sighup)
        except:
            log.info('This platform does not support signals.')

        # Start our worker threads
        for thread in self._worker.threads:
            thread.daemon = True
            thread.start()

        # Build our listening socket (with appropriate options)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if not self.socket:
            log.error("Failed to get socket.")
            raise socket.error
        try:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except:
            msg = "Cannot share socket.  Using {0}:{1} exclusively."
            log.warning(msg.format(self.address, self.port))
        try:
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except:
            msg = "Cannot set TCP_NODELAY, things might run a little slower"
            log.warning(msg)
        try:
            self.socket.bind((self.address,int(self.port)))
        except:
            msg = "Socket {0}:{1} in use by other process and it won't share."
            log.error(msg.format(self.address, self.port))
            sys.exit(1)
        self.socket.listen(socket.SOMAXCONN)

        try:
            msg = 'Listening on socket: {0}:{1}'
            log.info(msg.format(self.address, self.port))
            while not self._worker.stopServer:
                try:
                    if select([self.socket], [], [], 1.0)[0]:
                        self._worker.queue.put(self.socket.accept())
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

    def stop(self):
        log.info("Stopping Server")
        break_loop = 10
        W = self._worker

        for t in range(len(W.threads)):
            W.queue.put((None,None))

        time.sleep(1)

        while len(W.threads) and break_loop != 0:
            try:
                if 'client_socket' in W.threads:
                    log.debug("Shutting down client on thread")
                    W.threads.client.shutdown(socket.SHUT_RDWR)
                else:
                    break_loop -= 1
            except:
                log.warning('Failed to stop thread: \n'
                                + traceback.format_exc())
                break_loop -= 1

    def restart(self):
        self.stop()
        self.start()
