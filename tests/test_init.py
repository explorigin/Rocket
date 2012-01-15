# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2012 Timothy Farrell
#
# See the included LICENSE.txt file for licensing details.

# Import System Modules
import sys
import unittest
# Import Custom Modules
import rocket

# Define Constants
PY3K = sys.version_info[0] > 2

# Define Tests
class RocketInitTest(unittest.TestCase):
    def testMembers(self):
        members = ["VERSION", "SERVER_NAME", "SERVER_SOFTWARE", "HTTP_SERVER_SOFTWARE", "BUF_SIZE", "IS_JYTHON", "IGNORE_ERRORS_ON_CLOSE", "DEFAULT_LISTEN_QUEUE_SIZE", "DEFAULT_MIN_THREADS", "DEFAULT_MAX_THREADS", "DEFAULTS", "PY3K", "u", "b", "Rocket", "CherryPyWSGIServer"]
        for m in members:
            self.assertTrue(hasattr(rocket, m),
                         msg="rocket module does not have %s" % m)

    def testUnicode(self):
        if PY3K:
            self.skipTest("Not a valid test in Python 3")
        self.assertEqual(rocket.u('abc'), eval("u'abc'"))
        self.assertEqual(type(rocket.u('abc')), type(eval("u'abc'")))

    def testBytes(self):
        if PY3K:
            self.skipTest("Not a valid test in Python 3")
        self.assertEqual(rocket.b('abc'), 'abc')
        self.assertEqual(type(rocket.b('abc')), type('abc'))


if __name__ == '__main__':
    unittest.main()
