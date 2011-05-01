#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2009 Timothy Farrell

from distribute_setup import use_setuptools
use_setuptools()
from setuptools import setup, find_packages

import os
import sys
import re

if sys.version_info < (2, 5):
    raise Exception("Rocket requires Python 2.5 or higher.")

v = open(os.path.join(os.path.dirname(__file__), 'rocket', '__init__.py'))
VERSION = re.compile(r".*VERSION = '(.*?)'", re.S).match(v.read()).group(1)
v.close()
packages = find_packages(exclude=['tests'])

setup(name = "Rocket",
      version = VERSION,
      description = "Modern, Multi-threaded, Comet-Friendly WSGI Web Server",
      author = "Timothy Farrell",
      author_email = "explorigin@gmail.com",
      url = "http://www.launchpad.net/rocket",
      packages = packages,
      license = "MIT License",
      package_data = {'':['*.py', '*.txt']},
      include_package_data = True,
      install_requires=['distribute'],
      long_description = """The Rocket web server is a server designed to handle the increased needs of modern web applications implemented in pure Python. It can serve WSGI applications and middleware currently with the ability to be extended to handle different types of networked request-response jobs. Rocket runs on cPython 2.5-3.x and Jython 2.5 (without the need to run through the 2to3 translation tool). Rocket is similar in purpose to Cherrypy's Wsgiserver but with added flexibility, speed and concurrency.

Rocket Documentation is viewable at http://packages.python.org/rocket .

If you're searching for the rocket GAE framework, email mjpizz+rocket@gmail.com
""",
      classifiers = [
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.5",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 3",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Server",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers"],
      entry_points = {
        "distutils.commands": [
            "build_monolithic = monolithic:build_monolithic",
            "build_release = release:build_release",
        ],
    })
