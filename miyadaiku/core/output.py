import os
class Output:
    def __init__(self, dirname, name, stat, body):
        self.dirname = dirname
        self.name = name
        self.body = body
        self.stat = stat

    def write(self, path):
        dir = path.joinpath(*self.dirname)
        if not dir.is_dir():
            dir.mkdir(parents=True)
        dest = (dir / self.name)
        dest.write_bytes(self.body)

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
