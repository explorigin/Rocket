# -*- coding: utf-8 -*-

import sys
import socket
import logging
import traceback
from select import select

from . import SERVER_NAME
from .worker import get_method

class Rocket:
    def __init__(self,
                 app_info,
                 method='test',
                 bind_addr = ('127.0.0.1', 8000),
                 max_threads = 0,
                 min_threads = 10,
                 timeout = 10):

        self.address = bind_addr[0]
        self.port = bind_addr[1]

        self._worker = W = get_method(method)

        W.app_info = app_info
        W.stopServer = False
        W.min_threads = min_threads
        W.max_threads = max_threads
        W.timeout = timeout
        W.threads = set([W() for k in range(min_threads)])

    def start(self):
        for thread in self._worker.threads:
            thread.daemon = True
            thread.start()

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        if not self.socket:
            logging.error("Failed to get socket.")
            raise socket.error

        try:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except:
            msg = "Cannot share socket.  Using {0}:{1} exclusively."
            logging.warning(msg.format(self.address, self.port))

        try:
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except:
            msg = "Cannot set TCP_NODELAY, things might run a little slower"
            logging.warning(msg)

        try:
            self.socket.bind((self.address,int(self.port)))
        except:
            msg = "Socket {0}:{1} in use by other process and it won't share."
            logging.error(msg)
            sys.exit(1)

        self.socket.listen(socket.SOMAXCONN)

        try:
            while not self._worker.stopServer:
                try:
                    if select([self.socket], [], [], 1.0)[0]:
                        self._worker.queue.put(self.socket.accept())
                except KeyboardInterrupt:
                    return self.stop()
                except Exception:
                    logging.warn(str(traceback.format_exc()))
                    continue
        except:
            logging.error(str(traceback.format_exc()))
        return self.stop()

    def stop(self):
        logging.info("Stopping Server")
        break_loop = 10
        W = self._worker

        for t in range(len(W.threads)):
            W.queue.put((None,None))

        while len(W.threads) and break_loop != 0:
            try:
                if 'client_socket' in W.threads:
                    logging.debug("Shutting down client on thread")
                    W.threads.client_socket.shutdown(socket.SHUT_RDWR)
                else:
                    logging.debug("'client' not in thread")
                    break_loop -= 1
            except:
                logging.warning('Failed to stop thread: \n'
                                + traceback.format_exc())
                break_loop -= 1
