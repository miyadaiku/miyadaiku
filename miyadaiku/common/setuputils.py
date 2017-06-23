import os
import sys
from wheel import bdist_wheel
import distutils.dist

SETUP_FILE_EXTS = [
    '*.rst', '*.md', '*.html', '*.css', '*.js', '*.yml', '*.png',
    '*.jpg', '*.jpeg']

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



distutils.dist.Distribution.external_init= None

class bdist_wheel_ext(bdist_wheel.bdist_wheel):
    def run(self):
        if self.distribution.external_init:
            ret = os.system(self.distribution.external_init)
            if ret:
                raise RuntimeError(f'Command failed: {self.distribution.external_init!a}')
        return super().run()
