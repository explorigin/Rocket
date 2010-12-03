#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2010 Timothy Farrell
#
# See the included LICENSE.txt file for licensing details.

"test_all.py imports all the unittests and runs them, displaying the results."

# Import System Modules
import os
import sys
import types
import logging
import platform
import unittest
import traceback
from glob import glob
# Import 3rd Party Modules
### None ###
# Import Custom Modules
### None ###

# Define Constants
SLOW_TESTS = []
IS_JYTHON = platform.system() == 'Java'
logging.basicConfig(level=logging.CRITICAL)
PY3K = sys.version_info[0] > 2

def prnt(*args, **kwargs):
    sys.stdout.write(' '.join(args));
    
# Define Classes
class PrettyResults(unittest.TestResult):
    def __init__(self):
        self.currentTest = None
        unittest.TestResult.__init__(self)

    def startTest(self, test):
        self.testsRun += 1
        if self.currentTest != test.__module__:
            print('\nRunning test: %s' % test.__module__.split('.')[-1])
            self.currentTest = test.__module__

    def addSuccess(self, test):
        sys.stdout.write('.')

    def addFailure(self, test, err):
        err_rpt = ''.join(traceback.format_exception(*err))
        self.failures.append((test, err_rpt))
        print('F')
        print(err_rpt)

    def addError(self, test, err):
        err_rpt = ''.join(traceback.format_exception(*err))
        self.errors.append((test, err_rpt))
        print('E')
        print(err_rpt)

if __name__ == '__main__':
    args = sys.argv

    if len(args) > 1 and (args[1] == '-h' or args[1] == '--help'):
        usagemsg = ['Usage: %s (-h|--help) (-s|-slow)',
                    '',
                    '\t-h, --help\t display this text',
                    '\t-s, --slow\t Run slow tests']
        print('\n'.join(usagemsg) % (os.path.basename(args[0])))
        sys.exit();

    loader = unittest.TestLoader()
    sweet = unittest.TestSuite()
    result = PrettyResults()

    if IS_JYTHON:
        print('Testing on Jython ' + sys.version.split(' ')[0])
    else:
        print('Testing on Python ' + sys.version.split(' ')[0])

    print('Importing test modules...')

    mods = glob(os.path.join('tests','test_')+'*.py')
    modTotal = 0
    impfail = 0
    for x in [os.path.basename(y[:-3]) for y in mods]:
        if x not in SLOW_TESTS or (len(args) > 1 and args[1] == '-slow'):
            try:
                testMod = __import__('tests.' + x, fromlist=['tests'])
                sweet.addTests(loader.loadTestsFromModule(testMod))
                modTotal += 1
            except ImportError:
                impfail += 1
                tb_fmt = traceback.format_exception(sys.exc_info())
                print('Error loading module: %s\nMessage: %s' % (x, tb_fmt))
            except:
                impfail += 1
                print('Error loading module: ' + x)
                print(traceback.format_exc(sys.exc_info))

    print('Running %s tests in %i modules...' % (sweet.countTestCases(),
                                                       modTotal))

    sweet.run(result)

    fails = len(result.failures)
    errors = len(result.errors)
    msg = '\nSuccesses: %i, Errors: %i, Failures: %i, Failed Imports: %i'
    print(msg % (result.testsRun - fails - errors, errors, fails, impfail))

    for f in (glob('*'+os.path.sep+'*.pyc') + glob('*.pyc')):
        os.unlink(f)
