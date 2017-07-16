import os
import sys
import shutil
import glob
from wheel import bdist_wheel
import distutils.dist
from distutils.core import Command


SETUP_FILE_EXTS = [
    '*.rst', '*.md', '*.html', '*.css', '*.js', '*.yml', '*.png',
    '*.jpg', '*.jpeg', '*.otf', '*.eot', '*.svg', '*.ttf', '*.woff', '*.woff2', ]


def list_packages(packagedir, root):
    yield root

    dir = os.path.join(packagedir, root)
    for dirpath, dirnames, filenames in os.walk(dir):
        for d in dirnames:
            if not d.startswith('_'):
                path = os.path.join(dirpath, d)
                path = os.path.relpath(path, packagedir)
                yield path.replace(os.path.sep, '.')


def read_file(packagedir, fname):
    return open(os.path.join(packagedir, fname)).read()


distutils.dist.Distribution.exec_func = None


class exec_func(Command):
    description = 'Execute function'
    user_options = []
    boolean_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        if self.distribution.exec_func:
            self.distribution.exec_func(self.distribution)


distutils.dist.Distribution.copy_files = None


class copy_files(Command):
    description = 'Execute function'
    user_options = []
    boolean_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        if not self.distribution.copy_files:
            return

        for srcdir, specs, destdir in self.distribution.copy_files:
            for spec in specs:
                srcfiles = glob.glob(os.path.join(srcdir, spec))
                for fname in srcfiles:
                    print(f'copy {fname} -> {destdir}')
                    shutil.copy(fname, destdir)
