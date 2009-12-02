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

setup(name = "Rocket",
      version = VERSION,
      description = "Multi-threaded, Comet-Friendly HTTP Server",
      author = "Timothy Farrell",
      author_email = "tfarrell@owassobible.org",
      url = "http://www.launchpad.net/rocket",
      packages = find_packages(),
      license = "MIT License",
      long_description = "",
      classifiers = [
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.5",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 3",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Server",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        ]
      )
