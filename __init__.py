# -*- coding: utf-8 -*-

import sys
VERSION = '0.1'
SERVER_NAME = 'Rocket {0}'.format(VERSION)
HTTP_SERVER_NAME = '{0} Python/{1}'.format(SERVER_NAME,
                                           sys.version.split(' ')[0])
BUF_SIZE = 16384
py3k = sys.version_info[0] > 2

def b(n):
    """ Convert string/unicode/bytes literals into bytes.  This allows for the
    same code to run on Python 2.6 and Py3k. """
    if (py3k and isinstance(n, str)) or (not py3k and isinstance(n, unicode)):
        return n.encode()
    else:
        return n

def u(n, encoding="US-ASCII"):
    """ Convert bytes into string/unicode.  This allows for the
    same code to run on Python 2.6 and Py3k. """
    if (py3k and isinstance(n, bytes)) or (not py3k and isinstance(n, str)):
        return n.decode(encoding)
    else:
        return n
