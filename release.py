# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2009 Timothy Farrell

"""\
release.py is a module that contains the distutils add-in for creating
a monolithic source module of the Rocket web server.  To use get a monolithic
Rocket module first install Rocket normally.  Then run::

  setup.py build_release

The resulting monolithic module will be in the build/monolithic/ subdirectory.
"""

import os
import re
import sys
import shutil
import zipfile
from distribute_setup import use_setuptools
use_setuptools()
from setuptools import find_packages
from distutils.core import Command

v = open(os.path.join(os.path.dirname(__file__), 'rocket', '__init__.py'))
VERSION = re.compile(r".*VERSION = '(.*?)'", re.S).match(v.read()).group(1)
v.close()

class build_release(Command):
    user_options = []
    description = "Create release files."

    def initialize_options (self):
        self.builddir = os.path.join(os.getcwd(), 'build')
        self.temp = os.path.join(self.builddir, 'release')
        if os.path.exists(self.temp):
            shutil.rmtree(self.temp)
        os.makedirs(self.temp)

    def finalize_options (self):
        pass
    
    def _run_monolithic(self):
        os.system(sys.executable + ' setup.py build_monolithic')
        f = zipfile.ZipFile(os.path.join(self.temp,
                                         'Rocket-mono-'+VERSION+'.zip'), 'w')
        f.write(os.path.join(self.builddir, 'monolithic', 'rocket.py'),
                'rocket.py')
        f.close()
        
    def _run_docs(self):
        os.system(sys.executable + ' setup.py build_sphinx')
        f = zipfile.ZipFile(os.path.join(self.temp,
                                         'Rocket-docs-'+VERSION+'.zip'), 'w')
        sphinxdir = os.path.join(self.builddir, 'sphinx', 'html')
        for root, dirs, files in os.walk(sphinxdir):
            for filename in files:
                newroot = root[len(sphinxdir):]
                f.write(os.path.join(root, filename),
                        os.path.join(newroot, filename))
        f.close()
        
    
    def _run_src(self):
        temp = os.path.join(os.getcwd(), 'build', 'src')
        if os.path.exists(temp):
            shutil.rmtree(temp)
        os.makedirs(temp)
        os.system('bzr export ' + temp)
        f = zipfile.ZipFile(os.path.join(self.temp,
                                         'Rocket-src-'+VERSION+'.zip'), 'w')

        srcdir = os.path.join(self.builddir, 'src')
        for root, dirs, files in os.walk(srcdir):
            for filename in files:
                newroot = root[len(srcdir):]
                f.write(os.path.join(root, filename),
                        os.path.join(newroot, filename))
        f.close()

    def run(self):
        self._run_monolithic()
        self._run_docs()
        self._run_src()
        
       
        
