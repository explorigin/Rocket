# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2009 Timothy Farrell

# Import System Modules
import sys
import platform

# Define Constants
VERSION = '0.1'
SERVER_NAME = 'Rocket %s' % VERSION
HTTP_SERVER_NAME = '%s Python/%s' % (SERVER_NAME, sys.version.split(' ')[0])
BUF_SIZE = 16384
WAIT_QUEUE = 5
IS_JYTHON = platform.system() == 'Java' # Handle special cases for Jython

py3k = sys.version_info[0] > 2

def close_socket(sock):
    if hasattr(sock, '_sock'):
        sock._sock.close()
    sock.close()

if py3k:
    def b(n):
        """ Convert string/unicode/bytes literals into bytes.  This allows for
        the same code to run on Python 2.x and 3.x. """
        if isinstance(n, str):
            return n.encode()
        else:
            return n

    def u(n, encoding="us-ascii"):
        """ Convert bytes into string/unicode.  This allows for the
        same code to run on Python 2.x and 3.x. """
        if isinstance(n, bytes):
            return n.decode(encoding)
        else:
            return n

else:
    def b(n):
        """ Convert string/unicode/bytes literals into bytes.  This allows for
        the same code to run on Python 2.x and 3.x. """
        if isinstance(n, unicode):
            return n.encode()
        else:
            return n

    def u(n, encoding="us-ascii"):
        """ Convert bytes into string/unicode.  This allows for the
        same code to run on Python 2.x and 3.x. """
        if isinstance(n, str):
            return n.decode(encoding)
        else:
            return n
