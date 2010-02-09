# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2009 Timothy Farrell

"""\
monolithic.py is a module that contains the distutils add-in for creating
a monolithic source module of the Rocket web server.  To use get a monolithic
Rocket module first install Rocket normally.  Then run::

  setup.py build_monolithic

The resulting monolithic module will be in the build/monolithic/ subdirectory.
"""

import os
import re
from glob import glob
from distribute_setup import use_setuptools
use_setuptools()
from setuptools import find_packages
from distutils.core import Command

package_imports = re.compile(r'^(\s*from \.[\w\.]* import .*)$', re.I | re.M)

class build_monolithic(Command):
    user_options = []
    description = "Create a monolithic (one-file) source module."

    def initialize_options (self):
        self.files = []

    def finalize_options (self):
        packages = find_packages()
        for p in packages:
            self.files += sorted(glob(os.sep.join(p.split('.')) + os.sep + '*.py'))

    def run(self):
        build = self.get_finalized_command('build')
        filepath = os.path.join(build.build_base, 'monolithic', 'rocket.py')
        if os.path.exists(filepath):
            os.unlink(filepath)
        else:
            os.makedirs(os.path.dirname(filepath))

        out = open(filepath, 'w')

        first = True
        for filename in self.files:
            f = open(filename, 'r')
            filedata = f.readlines()
            f.close()

            if first:
                filedata = ''.join(filedata)
                first = False
            else:
                filedata = ''.join(filedata[4:])
                out.write("# Monolithic build...start of module: %s\r" % filename)

            i = 0
            templist = []
            showImportNotice = True
            for item in package_imports.finditer(filedata, i):
                out.write(filedata[i:item.start()])
                if showImportNotice:
                    out.write('# package imports removed in monolithic build')
                    showImportNotice = False
                i = item.end()

            out.write(filedata[i:len(filedata)])

            out.write("\r# Monolithic build...end of module: %s\r" % filename)

        out.close()
