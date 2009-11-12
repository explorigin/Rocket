# -*- coding: utf-8 -*-

import sys
VERSION = '0.1'
SERVER_NAME = 'Rocket %s' % VERSION
HTTP_SERVER_NAME = '%s Python/%s' % (SERVER_NAME, sys.version.split(' ')[0])
BUF_SIZE = 16384
py3k = sys.version_info[0] > 2

if py3k:
    def b(n):
        """ Convert string/unicode/bytes literals into bytes.  This allows for the
        same code to run on Python 2.6 and Py3k. """
        if isinstance(n, str):
            return n.encode()
        else:
            return n

    def u(n, encoding="us-ascii"):
        """ Convert bytes into string/unicode.  This allows for the
        same code to run on Python 2.6 and Py3k. """
        if isinstance(n, bytes):
            return n.decode(encoding)
        else:
            return n

else:
    def b(n):
        """ Convert string/unicode/bytes literals into bytes.  This allows for the
        same code to run on Python 2.6 and Py3k. """
        if isinstance(n, unicode):
            return n.encode()
        else:
            return n

    def u(n, encoding="us-ascii"):
        """ Convert bytes into string/unicode.  This allows for the
        same code to run on Python 2.6 and Py3k. """
        if isinstance(n, str):
            return n.decode(encoding)
        else:
            return n
