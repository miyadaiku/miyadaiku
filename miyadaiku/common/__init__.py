import os


def setup_list_packages(packagedir, root):
    yield root

    dir = os.path.join(packagedir, root)
    for dirpath, dirnames, filenames in os.walk(dir):
        for d in dirnames:
            if not d.startswith('_'):
                path = os.path.join(dirpath, d).replace(os.path.sep, '.')
                yield path


def setup_read_file(packagedir, fname):
    return open(os.path.join(packagedir, fname)).read()
