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
    
    
    def initialize_options (self):
        self.files = []

    def finalize_options (self):
        packages = find_packages()
        for p in packages:
            self.files += sorted(glob(os.sep.join(p.split('.')) + os.sep + '*.py'))
            
    def run(self):
        build = self.get_finalized_command('build')
        filepath = os.path.join(build.build_base, 'monolithic', 'rocket.py')
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
            
            i = 0
            templist = []
            for item in package_imports.finditer(filedata, i):
                out.write(filedata[i:item.start()])
                out.write('# ' + item.group() + ' # Monolithic Mode')
                i = item.end()
            
            out.write(filedata[i:len(filedata)])

        out.close()
        
