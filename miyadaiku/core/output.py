import os
import pathlib
import time
import collections

MKDIR_MAX_RETRY = 5
MKDIR_WAIT = 0.05


class Output:
    def __init__(self, dirname, name, stat, body, context):
        assert name
        self.dirname = dirname
        self.name = name
        self.body = body
        self.stat = stat
        self.context = context

    def write(self, path):
        dir = path.joinpath(*self.dirname)

        for i in range(MKDIR_MAX_RETRY):
            if dir.is_dir():
                break
            try:
                dir.mkdir(parents=True)
            except FileExistsError:
                pass
            time.sleep(MKDIR_WAIT)

        dest = self.calc_path(path, self.dirname, self.name)

        s = str(path)
        if not dest.startswith(s) or dest[len(s)] not in '\\/':
            raise ValueError(f"Invalid file name: {self.name}")

        destfile = pathlib.Path(dest)
        destfile.write_bytes(self.body)

        if self.stat:
            os.utime(dest, (self.stat.st_atime, self.stat.st_mtime))
            os.chmod(dest, self.stat.st_mode)

        return destfile


class Output:
    @staticmethod
    def calc_path(path, dirname, name):
        dir = path.joinpath(*dirname)
        name = name.strip('/\\')
        dest = os.path.expanduser((dir / name))
        dest = os.path.normpath(dest)
        return dest

    def __init__(self, content, filename, *args, **kwargs):
        self.content = content
        self.filename = filename

        self.args = args
        self.kwargs = kwargs

    def build(self, path):
        dir = path.joinpath(*self.content.dirname)
        for i in range(MKDIR_MAX_RETRY):
            if dir.is_dir():
                break
            try:
                dir.mkdir(parents=True)
            except FileExistsError:
                pass
            time.sleep(MKDIR_WAIT)

        dest = self.calc_path(path, self.content.dirname, self.filename)
        s = str(path)

        if not dest.startswith(s) or dest[len(s)] not in '\\/':
            raise ValueError(f"Invalid file name: {self.content.filename}")

        context = self.content.write(pathlib.Path(dest), *self.args, **self.kwargs)

        if self.content.stat:
            os.utime(dest, (self.content.stat.st_atime, self.content.stat.st_mtime))
            os.chmod(dest, self.content.stat.st_mode)

        return dest, context


class Outputs:
    def __init__(self):
        self._files = {}

    def add(self, output):
        self._files[(output.content.dirname, output.content.name)] = output

    def get(self, k):
        return self._files[k]
