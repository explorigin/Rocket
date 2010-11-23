# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2010 Timothy Farrell

# Import System Modules
import os
import socket
import logging
import traceback
from threading import Thread
try:
    from queue import Queue
except ImportError:
    from Queue import Queue

try:
    import ssl
    from ssl import SSLError
    has_ssl = True
except ImportError:
    has_ssl = False
    class SSLError(socket.error):
        pass
# Import Package Modules
from . import SERVER_NAME, BUF_SIZE, IS_JYTHON, IGNORE_ERRORS_ON_CLOSE, b, PY3K, NullHandler, POLL_TIMEOUT
from .connection import Connection

class Listener(Thread):
    """The Listener class is a class responsible for accepting connections
    and queuing them to be processed by a worker thread."""

    def __init__(self, interface, queue_size, threadpool, *args, **kwargs):
        Thread.__init__(self, *args, **kwargs)
        self.err_log = logging.getLogger('Rocket.Errors.'+self.getName())
        self.err_log.addHandler(NullHandler())
        
        self.threadpool = threadpool
        self.interface = interface
        self.addr = interface[0]
        self.port = interface[1]
        self.secure = len(interface) == 4 and interface[2] != '' and interface[3] != ''
        self.ready = False

        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        if not listener:
            self.err_log.error("Failed to get socket.")
            return

        if self.secure:
            if not has_ssl:
                self.err_log.error("ssl module required to serve HTTPS.")
                del listener
                return
            elif not os.path.exists(interface[2]):
                data = (interface[2], interface[0], interface[1])
                self.err_log.error("Cannot find key file "
                          "'%s'.  Cannot bind to %s:%s" % data)
                del listener
                return
            elif not os.path.exists(interface[3]):
                data = (interface[3], interface[0], interface[1])
                self.err_log.error("Cannot find certificate file "
                          "'%s'.  Cannot bind to %s:%s" % data)
                del listener
                return

        # Set socket options
        try:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except:
            msg = "Cannot share socket.  Using %s:%i exclusively."
            self.err_log.warning(msg % (self.addr, self.port))

        try:
            if not IS_JYTHON:
                listener.setsockopt(socket.IPPROTO_TCP,
                                    socket.TCP_NODELAY,
                                    1)
        except:
            msg = "Cannot set TCP_NODELAY, things might run a little slower"
            self.err_log.warning(msg)

        try:
            listener.bind((self.addr, self.port))
        except:
            msg = "Socket %s:%i in use by other process and it won't share."
            self.err_log.error(msg % (self.addr, self.port))
        else:
            if IS_JYTHON:
                # Jython requires a socket to be in Non-blocking mode in order
                # to select on it.
                listener.setblocking(False)
            else:
                # Otherwise, we want socket operations to timeout so as to not
                # tie up threads.
                listener.settimeout(POLL_TIMEOUT)
            # Listen for new connections allowing queue_size number of
            # connections to wait before rejecting a connection.
            listener.listen(queue_size)
            
            self.listener = listener

            self.ready = True


    def run(self):
        if not self.ready:
            self.err_log.warning('Listener started when not ready.')
            return

        self.err_log.debug('Entering main loop.')
        while True:
            try:
                sock = self.listener.accept()
                if self.secure:
                    try:
                        sock = (ssl.wrap_socket(sock[0],
                                                keyfile=self.interface[2],
                                                certfile=self.interface[3],
                                                server_side=True,
                                                ssl_version=ssl.PROTOCOL_SSLv23), sock[1])
                    except SSLError:
                        # Generally this happens when an HTTP request is received on a secure socket.
                        # We don't do anything because it will be detected by Worker and dealt with
                        # appropriately.
                        pass
                self.threadpool.queue.put((sock, self.interface[1], self.secure))

            except socket.timeout:
                # socket.timeout will be raised every POLL_TIMEOUT seconds
                # When that happens, we check if it's time to die.
                
                if not self.ready:
                    self.err_log.info('Listener exiting.')
                    return
                else:
                    continue

            except KeyboardInterrupt:
                # Capture a keyboard interrupt when running from a console
                return
            except:
                if not self.threadpool.stop_server:
                    self.err_log.error(str(traceback.format_exc()))

    def run_app(self, conn):
        # Must be overridden with a method reads the request from the socket
        # and sends a response.
        self.closeConnection = True
        raise NotImplementedError('Overload this method!')

    def kill(self):
        if self.isAlive() and hasattr(self, 'conn'):
            try:
                self.conn.shutdown(socket.SHUT_RDWR)
            except socket.error:
                info = sys.exc_info()
                if info[1].args[0] != socket.EBADF:
                    self.err_log.debug('Error on shutdown: '+str(info))
