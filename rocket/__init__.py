# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2010 Timothy Farrell

# Import System Modules
import sys
import errno
import socket
import logging
import platform

# Define Constants
VERSION = '1.0.6'
SERVER_NAME = socket.gethostname()
SERVER_SOFTWARE = 'Rocket %s' % VERSION
HTTP_SERVER_SOFTWARE = '%s Python/%s' % (SERVER_SOFTWARE, sys.version.split(' ')[0])
BUF_SIZE = 16384
POLL_TIMEOUT = 1
IS_JYTHON = platform.system() == 'Java' # Handle special cases for Jython
IGNORE_ERRORS_ON_CLOSE = set([errno.ECONNABORTED, errno.ECONNRESET])
DEFAULT_LISTEN_QUEUE_SIZE = 5
DEFAULT_MIN_THREADS = 10
DEFAULT_MAX_THREADS = 128
DEFAULTS = dict(LISTEN_QUEUE_SIZE = DEFAULT_LISTEN_QUEUE_SIZE,
                MIN_THREADS = DEFAULT_MIN_THREADS,
                MAX_THREADS = DEFAULT_MAX_THREADS)

PY3K = sys.version_info[0] > 2

class NullHandler(logging.Handler):
    "A Logging handler to prevent library errors."
    def emit(self, record):
        pass

if PY3K:
    def b(val):
        """ Convert string/unicode/bytes literals into bytes.  This allows for
        the same code to run on Python 2.x and 3.x. """
        if isinstance(val, str):
            return val.encode()
        else:
            return val

    def u(val, encoding="us-ascii"):
        """ Convert bytes into string/unicode.  This allows for the
        same code to run on Python 2.x and 3.x. """
        if isinstance(val, bytes):
            return val.decode(encoding)
        else:
            return val

else:
    def b(val):
        """ Convert string/unicode/bytes literals into bytes.  This allows for
        the same code to run on Python 2.x and 3.x. """
        if isinstance(val, unicode):
            return val.encode()
        else:
            return val

    def u(val, encoding="us-ascii"):
        """ Convert bytes into string/unicode.  This allows for the
        same code to run on Python 2.x and 3.x. """
        if isinstance(val, str):
            return val.decode(encoding)
        else:
            return val

# Import Package Modules
from .main import Rocket, CherryPyWSGIServer

__all__ = ['VERSION', 'SERVER_SOFTWARE', 'HTTP_SERVER_SOFTWARE', 'BUF_SIZE',
           'IS_JYTHON', 'IGNORE_ERRORS_ON_CLOSE', 'DEFAULTS', 'PY3K', 'b', 'u',
           'Rocket', 'CherryPyWSGIServer', 'SERVER_NAME', 'NullHandler']
