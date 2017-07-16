import os
import pathlib


class Output:
    def __init__(self, dirname, name, stat, body):
        assert name
        self.dirname = dirname
        self.name = name
        self.body = body
        self.stat = stat

    def write(self, path):
        dir = path.joinpath(*self.dirname)
        if not dir.is_dir():
            dir.mkdir(parents=True)

        name = self.name.strip('/\\')
        dest = os.path.expanduser((dir / name))
        dest = os.path.normpath(dest)

        s = str(path)
        if not dest.startswith(s) or dest[len(s)] not in '\\/':
            raise ValueError(f"Invalid file name: {self.name}")

        destfile = pathlib.Path(dest)
        destfile.write_bytes(self.body)

        if self.stat:
            os.utime(dest, (self.stat.st_atime, self.stat.st_mtime))
            os.chmod(dest, self.stat.st_mode)


class Outputs:
    def __init__(self):
        self._files = {}

    def add(self, output):
        self._files[(output.dirname, output.name)] = output

    def write(self, path):
        for output in self._files.values():
            output.write(path)
